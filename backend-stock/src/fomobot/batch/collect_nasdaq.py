"""
NASDAQ 가격 데이터 수집 배치.

- 데이터 소스: yfinance (auto_adjust=True → 수정주가)
- 티커 목록:   NASDAQ 공개 CSV (nasdaqlisted.txt)
- 배치 방식:   100개씩 묶음 다운로드, 배치 간 2초 딜레이
- 재시도:      tenacity exponential backoff, 연속 5배치 실패 시 30분 대기
- 스케줄:      매일 07:30 KST (NYSE 장 마감 16:00 EST = KST 06:00 + 여유 1.5h)
"""

import io
import logging
import time
from datetime import date, timedelta

import pandas as pd
import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from fomobot.config import settings
from fomobot.db.crud import upsert_price_daily_sync, upsert_index_daily_sync
from fomobot.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)

MARKET = "nasdaq"
INDEX_CODE = "QQQ"
NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"


def fetch_nasdaq_tickers() -> list[str]:
    """
    NASDAQ 공개 디렉토리에서 상장 종목 티커를 조회한다.
    파이프(|) 구분자, 마지막 줄은 파일 생성 날짜(제거 필요).
    """
    try:
        resp = httpx.get(NASDAQ_LISTED_URL, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), sep="|")
        # 마지막 행은 메타 정보 행 제거
        df = df[df["Symbol"].notna() & ~df["Symbol"].str.startswith("File", na=False)]
        # ETF 제외 (주식만)
        if "ETF" in df.columns:
            df = df[df["ETF"] != "Y"]
        tickers = df["Symbol"].str.strip().tolist()
        # 특수문자 포함 티커 제거 (클래스 주식 등 yfinance가 처리 못하는 경우)
        tickers = [t for t in tickers if t.isalpha() and len(t) <= 5]
        logger.info("NASDAQ 티커 %d개 로드", len(tickers))
        return tickers
    except Exception:
        logger.exception("NASDAQ 티커 목록 조회 실패, 폴백 목록 사용")
        # 최소 폴백: NASDAQ 100 핵심 종목
        return [
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG",
            "TSLA", "AVGO", "COST", "NFLX", "AMD", "ADBE", "QCOM", "INTC",
        ]


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _download_batch(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """yfinance 배치 다운로드 (수정주가)."""
    import yfinance as yf
    df = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        group_by="ticker",
        progress=False,
        threads=False,   # 멀티스레드 OFF → 레이트리밋 방지
    )
    return df


def _parse_batch_df(
    df: pd.DataFrame,
    tickers: list[str],
    market: str,
) -> list[dict]:
    """
    yfinance 배치 결과를 price_daily 레코드 리스트로 변환.

    단일 티커 조회 시 컬럼 구조가 다름 (MultiIndex 없음) → 두 경우 모두 처리.
    """
    records: list[dict] = []

    if df.empty:
        return records

    # 단일 티커면 MultiIndex가 없음
    if len(tickers) == 1:
        ticker = tickers[0]
        sub = df
        _append_ticker_records(records, sub, ticker, market)
        return records

    # 다중 티커: MultiIndex(ticker, field)
    for ticker in tickers:
        if ticker not in df.columns.get_level_values(0):
            continue
        sub = df[ticker].dropna(how="all")
        if sub.empty:
            continue
        _append_ticker_records(records, sub, ticker, market)

    return records


def _append_ticker_records(
    records: list[dict],
    sub: pd.DataFrame,
    ticker: str,
    market: str,
) -> None:
    for row in sub.itertuples():
        close_val = getattr(row, "Close", None)
        if pd.isna(close_val):
            continue

        open_val = getattr(row, "Open", None)
        high_val = getattr(row, "High", None)
        low_val = getattr(row, "Low", None)
        volume_val = getattr(row, "Volume", None)

        idx_date = row.Index

        records.append({
            "ticker": ticker,
            "market": market,
            "date": idx_date.date() if hasattr(idx_date, "date") else idx_date,
            "open": float(open_val) if pd.notna(open_val) and open_val is not None else None,
            "high": float(high_val) if pd.notna(high_val) and high_val is not None else None,
            "low": float(low_val) if pd.notna(low_val) and low_val is not None else None,
            "close_adj": float(close_val) if close_val is not None else 0.0,
            "volume": int(volume_val) if pd.notna(volume_val) and volume_val is not None else None,
            "market_cap": None,  # yfinance 배치에서 시총은 별도 조회 비용이 크므로 생략
        })


def run_nasdaq_collection(target_date: date | None = None) -> None:
    """
    NASDAQ 전 종목 가격 데이터를 수집해 DB에 저장한다.

    Parameters
    ----------
    target_date : date | None
        수집 기준일. None이면 오늘 날짜 사용.
    """
    today = target_date or date.today()
    start_date = today - timedelta(days=7)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")  # yfinance end는 exclusive

    logger.info("NASDAQ 수집 시작: %s ~ %s", start_str, end_str)

    tickers = fetch_nasdaq_tickers()
    batch_size = settings.batch_size_nasdaq
    batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]

    all_records: list[dict] = []
    consecutive_failures = 0

    for batch_idx, batch in enumerate(batches):
        # 서킷 브레이커: 연속 실패가 임계값 초과 시 대기 후 재개
        if consecutive_failures >= settings.nasdaq_max_consec_failures:
            wait_sec = settings.nasdaq_circuit_breaker_wait_sec
            logger.warning(
                "NASDAQ 연속 %d배치 실패, %d분 대기 후 재개",
                consecutive_failures, wait_sec // 60,
            )
            time.sleep(wait_sec)
            consecutive_failures = 0

        try:
            df = _download_batch(batch, start_str, end_str)
            records = _parse_batch_df(df, batch, MARKET)
            all_records.extend(records)
            consecutive_failures = 0

            logger.debug("배치 %d/%d: %d건 수집", batch_idx + 1, len(batches), len(records))

        except Exception:
            logger.warning("NASDAQ 배치 %d/%d 실패, 스킵", batch_idx + 1, len(batches))
            consecutive_failures += 1
            continue

        # 배치 간 딜레이
        time.sleep(settings.nasdaq_batch_delay_sec)

        # 메모리 절약: 5000건마다 중간 저장
        if len(all_records) >= 5_000:
            with SyncSessionLocal() as session:
                upsert_price_daily_sync(session, all_records)
            logger.info("NASDAQ 중간 저장: %d건", len(all_records))
            all_records.clear()

    # QQQ 지수 수집 (NASDAQ 대용 지수)
    index_records: list[dict] = []
    try:
        df_qqq = _download_batch(["QQQ"], start_str, end_str)
        if not df_qqq.empty:
            close_series = df_qqq["Close"] if "Close" in df_qqq.columns else df_qqq["QQQ"]["Close"]
            for idx_date, val in close_series.items():
                if pd.notna(val):
                    index_records.append({
                        "index_code": INDEX_CODE,
                        "date": idx_date.date(),
                        "close_adj": float(val),
                    })
    except Exception:
        logger.warning("QQQ 지수 수집 실패")

    with SyncSessionLocal() as session:
        if all_records:
            upsert_price_daily_sync(session, all_records)
            logger.info("NASDAQ 가격 최종 저장: %d건", len(all_records))
        if index_records:
            upsert_index_daily_sync(session, index_records)
            logger.info("QQQ 지수 %d건 저장", len(index_records))

    logger.info("NASDAQ 수집 완료")


def run_nasdaq_full_history(start_date: date, end_date: date) -> None:
    """초기 풀 히스토리 수집 (CLI로 1회 실행)."""
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")

    logger.info("NASDAQ 풀 히스토리 수집: %s ~ %s", start_str, end_str)

    tickers = fetch_nasdaq_tickers()
    batch_size = settings.batch_size_nasdaq
    batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]

    all_records: list[dict] = []
    consecutive_failures = 0

    for batch_idx, batch in enumerate(batches):
        if consecutive_failures >= settings.nasdaq_max_consec_failures:
            wait_sec = settings.nasdaq_circuit_breaker_wait_sec
            logger.warning("서킷 브레이커 발동, %d분 대기", wait_sec // 60)
            time.sleep(wait_sec)
            consecutive_failures = 0

        try:
            df = _download_batch(batch, start_str, end_str)
            records = _parse_batch_df(df, batch, MARKET)
            all_records.extend(records)
            consecutive_failures = 0
        except Exception:
            logger.warning("배치 %d/%d 실패", batch_idx + 1, len(batches))
            consecutive_failures += 1
            continue

        time.sleep(settings.nasdaq_batch_delay_sec)

        if len(all_records) >= 10_000:
            with SyncSessionLocal() as session:
                upsert_price_daily_sync(session, all_records)
            logger.info("중간 저장 %d건", len(all_records))
            all_records.clear()

        if (batch_idx + 1) % 10 == 0:
            logger.info("진행률: %d/%d 배치", batch_idx + 1, len(batches))

    with SyncSessionLocal() as session:
        if all_records:
            upsert_price_daily_sync(session, all_records)
    logger.info("NASDAQ 풀 히스토리 수집 완료")

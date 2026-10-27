"""
NASDAQ 가격 데이터 수집 배치.

- 데이터 소스: yfinance (auto_adjust=False → raw Close 사용.
  raw Close는 분할이 이미 내재 반영되어 있고 배당은 미반영된 값이므로
  close_adj = raw Close 그대로 저장한다. 배당 재조정 절대 금지 — 2026-07-29
  조사에서 auto_adjust=True의 배당 소급조정이 CBIO 등에서 close_adj를
  음수로 만드는 원인임을 확인함.)
- 티커 목록:   NASDAQ 공개 CSV (nasdaqlisted.txt)
- 배치 방식:   100개씩 묶음 다운로드, 배치 간 2초 딜레이
- 재시도:      tenacity exponential backoff, 연속 5배치 실패 시 30분 대기
- 스케줄:      매일 07:30 KST (NYSE 장 마감 16:00 EST = KST 06:00 + 여유 1.5h)
"""

import hashlib
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
from fomobot.db.crud import (
    upsert_price_daily_sync,
    upsert_index_daily_sync,
    upsert_securities_master_sync,
)
from fomobot.db.session import SyncSessionLocal
from fomobot.services.nasdaq_listing import is_when_issued_symbol, normalize_security_name

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
        # when-issued 티커는 정식 티커와 별도 심볼로 상장되므로 그대로 두면 같은
        # 회사가 이중 집계된다(2026-10 확인: MMEDV/MMED 등). 조용히 빼지 않고 로그로 남긴다.
        when_issued = [t for t in tickers if is_when_issued_symbol(t)]
        if when_issued:
            logger.info("NASDAQ when-issued 티커 %d개 제외: %s", len(when_issued), when_issued)
            tickers = [t for t in tickers if not is_when_issued_symbol(t)]
        logger.info("NASDAQ 티커 %d개 로드", len(tickers))
        return tickers
    except Exception:
        logger.exception("NASDAQ 티커 목록 조회 실패, 폴백 목록 사용")
        # 최소 폴백: NASDAQ 100 핵심 종목
        return [
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG",
            "TSLA", "AVGO", "COST", "NFLX", "AMD", "ADBE", "QCOM", "INTC",
        ]


def _fetch_nasdaq_name_map() -> dict[str, str]:
    """nasdaqlisted.txt에서 ticker→종목명 매핑을 반환한다. 실패 시 빈 dict."""
    try:
        resp = httpx.get(NASDAQ_LISTED_URL, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), sep="|")
        df = df[df["Symbol"].notna() & ~df["Symbol"].str.startswith("File", na=False)]
        if "ETF" in df.columns:
            df = df[df["ETF"] != "Y"]
        df = df[df["Symbol"].str.isalpha() & (df["Symbol"].str.len() <= 5)]
        if "Security Name" not in df.columns:
            return {}
        names = df["Security Name"].map(
            lambda s: normalize_security_name(s)[:200] if isinstance(s, str) else s
        )
        return dict(zip(df["Symbol"].str.strip(), names))
    except Exception:
        logger.warning("NASDAQ 종목명 매핑 조회 실패")
        return {}


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _download_batch(tickers: list[str], start: str, end: str, actions: bool = False) -> pd.DataFrame:
    """
    yfinance 배치 다운로드 (split-only 조정).

    auto_adjust=False로 받은 raw Close를 그대로 close_adj로 쓴다.
    raw Close에는 분할이 반영돼 있지만 소급 반영이 항상 완전하지는 않다
    (2026-10 확인: 분할일에 절벽이 그대로 남은 종목, 분할 직전 며칠만 미조정인 종목).
    배당은 반영하지 않는다(_append_ticker_records에서 Close만 사용, Adj Close는 무시).

    actions=True면 "Dividends"/"Stock Splits" 열이 추가된다 — 분할 감지(extract_splits)용.
    """
    import yfinance as yf
    df = yf.download(
        tickers,
        start=start,
        end=end,
        actions=actions,
        auto_adjust=False,
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

    단일 티커 조회 시 컬럼 구조가 다를 수 있음 (MultiIndex 없는 경우) → 두 경우 모두 처리.
    티커 개수가 아니라 실제 반환된 컬럼 구조로 판단한다 — auto_adjust=False에서는
    "Adj Close" 컬럼이 추가되어 단일 티커여도 MultiIndex가 유지되는 경우가 있다
    (auto_adjust=True일 때만 단일 티커 → flat 컬럼이었음, 2026-07-29 확인).
    """
    records: list[dict] = []

    if df.empty:
        return records

    # 단일 티커이면서 MultiIndex가 아닌 경우(flat 컬럼)만 특별 처리
    if len(tickers) == 1 and not isinstance(df.columns, pd.MultiIndex):
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


def extract_splits(df: pd.DataFrame, tickers: list[str]) -> list[dict]:
    """
    actions=True로 받은 배치 응답의 "Stock Splits" 열에서 분할을 읽는다.

    값은 새 주식 수 / 옛 주식 수다 (0.5 = 1-for-2 역분할, 2.0 = 2-for-1 정분할).
    파싱 실패가 가격 수집을 막으면 안 되므로 예외는 삼키고 빈 목록을 돌려준다.
    """
    found: list[dict] = []
    try:
        if df.empty:
            return found
        if len(tickers) == 1 and not isinstance(df.columns, pd.MultiIndex):
            frames = {tickers[0]: df}
        else:
            level0 = df.columns.get_level_values(0)
            frames = {t: df[t] for t in tickers if t in level0}
        for ticker, sub in frames.items():
            if "Stock Splits" not in sub.columns:
                continue
            s = sub["Stock Splits"].dropna()
            for idx, ratio in s[(s > 0) & (s != 1)].items():
                found.append({
                    "ticker": ticker,
                    "date": idx.date() if hasattr(idx, "date") else idx,
                    "ratio": float(ratio),
                })
    except Exception:
        logger.warning("분할 열 파싱 실패 — 이번 배치 분할 감지 생략", exc_info=True)
    return found


# 이 일수 안의 분할만 Sentry로 알린다. 수집 구간이 7일이라 같은 분할이 매일 다시 잡히는데,
# 분할은 일어난 날의 수집에서 처음 잡히므로 최근 것만 알리면 대부분 한 번만 알림이 간다.
SPLIT_ALERT_RECENT_DAYS = 2
SPLIT_ALERT_LIMIT = 30  # 알림 한 건에 상세 표기할 분할 수 (전체는 로그에 남는다)


def report_splits(splits: list[dict], today: date | None = None) -> None:
    """
    수집 구간에서 감지한 분할을 로그에 모두 남기고, 최근 분할은 Sentry 경고 한 건으로 요약해 알린다.

    절벽 탐지는 종가 비율 0.35~3배 밖만 잡아서 1-for-2 같은 소규모 분할은 DB가
    오염돼도 알림이 없다(GCTK 2026-10-26). 분할 자체를 감지해 그 사각을 메운다.

    2026-10-26 첫 실행에서 분할이 21건(7일 창)이라 분할마다 이벤트를 보내자 그 시간대에
    Sentry가 이벤트를 거부했다(too_large:event 27건, 전송 실패 25건). 그래서 실행당 한 건으로
    요약하고, 수집 중 쌓인 breadcrumb 없이 작게 보내며, 전달 결과를 로그로 남긴다.
    """
    today = today or date.today()
    for s in splits:
        logger.warning("[NASDAQ] 분할 감지 %s %s ratio=%g", s["ticker"], s["date"], s["ratio"])

    recent = sorted(
        (s for s in splits if (today - s["date"]).days <= SPLIT_ALERT_RECENT_DAYS),
        key=lambda s: (s["date"], s["ticker"]), reverse=True,
    )
    if not recent:
        return

    def fmt(s: dict) -> str:
        kind = "역분할" if s["ratio"] < 1 else "정분할"
        return f"{s['ticker']} {s['date']:%m-%d} {kind} {s['ratio']:g}(x{1 / s['ratio']:.2f})"

    shown = ", ".join(fmt(s) for s in recent[:SPLIT_ALERT_LIMIT])
    rest = len(recent) - SPLIT_ALERT_LIMIT
    message = (
        f"[NASDAQ] 분할 감지 {len(recent)}건(최근 {SPLIT_ALERT_RECENT_DAYS}일): {shown}"
        + (f" 외 {rest}건" if rest > 0 else "")
        + " | 수집 구간 경계에서 DB 가격이 불연속일 수 있다. 절벽 탐지는 0.35~3배 밖만 잡으므로 "
        "소규모 분할은 직접 확인 필요"
    )
    # 같은 분할 집합이면 같은 이슈로 묶는다 (구간이 겹쳐 연속 실행에서 반복될 때)
    digest = hashlib.md5(",".join(sorted(f"{s['ticker']}:{s['date']}" for s in recent)).encode()).hexdigest()[:12]
    try:
        import sentry_sdk
        with sentry_sdk.isolation_scope() as scope:
            scope.clear_breadcrumbs()
            scope.fingerprint = ["nasdaq-split-detected", digest]
            event_id = sentry_sdk.capture_message(message, level="warning")
        sentry_sdk.flush(timeout=5)
        logger.info("분할 감지 Sentry 전송: %d건, event_id=%s", len(recent), event_id)
    except Exception:
        logger.warning("분할 감지 Sentry 전송 실패", exc_info=True)


def run_nasdaq_collection(target_date: date | None = None) -> date:
    """
    NASDAQ 전 종목 가격 데이터를 수집해 DB에 저장한다.

    Parameters
    ----------
    target_date : date | None
        수집 기준일. None이면 오늘 날짜 사용.

    Returns
    -------
    date : 이번 실행이 다시 조회한 구간의 시작일. 이 날짜 이후 행은 늦게 도착한
        데이터로 새로 채워졌을 수 있으므로, breadth는 이 날짜부터 다시 계산한다.
    """
    today = target_date or date.today()
    start_date = today - timedelta(days=7)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")  # yfinance end는 exclusive

    logger.info("NASDAQ 수집 시작: %s ~ %s", start_str, end_str)

    name_map = _fetch_nasdaq_name_map()
    tickers = fetch_nasdaq_tickers()
    batch_size = settings.batch_size_nasdaq
    batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]

    all_records: list[dict] = []
    detected_splits: list[dict] = []
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
            df = _download_batch(batch, start_str, end_str, actions=True)
            records = _parse_batch_df(df, batch, MARKET)
            all_records.extend(records)
            detected_splits.extend(extract_splits(df, batch))
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

    report_splits(detected_splits, today)

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

    master_records = [
        {"ticker": t, "market": MARKET, "name": name_map.get(t), "is_active": True}
        for t in tickers
    ]

    with SyncSessionLocal() as session:
        if all_records:
            upsert_price_daily_sync(session, all_records)
            logger.info("NASDAQ 가격 최종 저장: %d건", len(all_records))
        if index_records:
            upsert_index_daily_sync(session, index_records)
            logger.info("QQQ 지수 %d건 저장", len(index_records))
        if master_records:
            upsert_securities_master_sync(session, master_records)
            logger.info("NASDAQ securities_master %d건 저장 완료", len(master_records))

    logger.info("NASDAQ 수집 완료")
    return start_date


def _get_covered_tickers(market: str, start_date: date, end_date: date, min_rows: int = 100) -> set[str]:
    """DB에 min_rows 이상의 데이터가 있는 티커를 반환한다."""
    from sqlalchemy import text
    with SyncSessionLocal() as session:
        rows = session.execute(
            text(
                "SELECT ticker FROM price_daily "
                "WHERE market = :market AND date BETWEEN :start AND :end "
                "GROUP BY ticker HAVING COUNT(*) >= :min_rows"
            ),
            {"market": market, "start": start_date, "end": end_date, "min_rows": min_rows},
        ).fetchall()
    return {r[0] for r in rows}


def run_nasdaq_full_history(start_date: date, end_date: date) -> None:
    """초기 풀 히스토리 수집 (CLI로 1회 실행). 이미 데이터가 있는 티커는 스킵."""
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")

    logger.info("NASDAQ 풀 히스토리 수집: %s ~ %s", start_str, end_str)

    name_map = _fetch_nasdaq_name_map()
    all_tickers = fetch_nasdaq_tickers()

    covered = _get_covered_tickers(MARKET, start_date, end_date)
    tickers = [t for t in all_tickers if t not in covered]
    logger.info(
        "NASDAQ: 전체 %d개 중 %d개 스킵(기존 데이터), %d개 수집 예정",
        len(all_tickers), len(covered), len(tickers),
    )

    if not tickers:
        logger.info("모든 NASDAQ 티커의 데이터가 이미 존재합니다.")
        return

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

    master_records = [
        {"ticker": t, "market": MARKET, "name": name_map.get(t), "is_active": True}
        for t in tickers
    ]

    with SyncSessionLocal() as session:
        if all_records:
            upsert_price_daily_sync(session, all_records)
        if master_records:
            upsert_securities_master_sync(session, master_records)
            logger.info("NASDAQ securities_master %d건 저장 완료", len(master_records))
    logger.info("NASDAQ 풀 히스토리 수집 완료")

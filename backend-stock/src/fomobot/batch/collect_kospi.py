"""
KOSPI 가격 데이터 수집 배치.

- 데이터 소스: pykrx (KRX 홈페이지 크롤링)
- 수정주가:    get_market_ohlcv_by_date(..., adjusted=True)
- 시총:        get_market_cap_by_date()
- 스케줄:      매일 18:00 KST (장 마감 15:30 + 여유 2.5h)
- 재시도:      tenacity exponential backoff (max 3회)
"""

import logging
import time
from datetime import date, timedelta

import pandas as pd
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from fomobot.db.crud import (
    upsert_price_daily_sync,
    upsert_index_daily_sync,
    upsert_securities_master_sync,
)
from fomobot.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)

MARKET = "kospi"
INDEX_CODE = "KOSPI"
# KOSPI 지수 티커 (pykrx)
KOSPI_INDEX_TICKER = "1001"


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_ohlcv(start: str, end: str, ticker: str, adjusted: bool = True) -> pd.DataFrame:
    from pykrx import stock
    return stock.get_market_ohlcv_by_date(start, end, ticker, adjusted=adjusted)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_market_cap(start: str, end: str, ticker: str) -> pd.DataFrame:
    from pykrx import stock
    return stock.get_market_cap_by_date(start, end, ticker)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_ticker_list(date: str = "") -> list[str]:
    from pykrx import stock
    return stock.get_market_ticker_list(date, market="KOSPI")


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_ticker_name(ticker: str) -> str:
    from pykrx import stock
    return stock.get_market_ticker_name(ticker)


def _fetch_ticker_name_safe(ticker: str) -> str | None:
    """재시도 없이 종목명 1회 조회. 실패 시 None 반환."""
    try:
        from pykrx import stock
        return stock.get_market_ticker_name(ticker)
    except Exception:
        return None


def _fetch_kospi_index(start: str, end: str) -> pd.DataFrame:
    """KOSPI 지수 수정주가 조회."""
    from pykrx import stock
    df = stock.get_index_ohlcv_by_date(start, end, KOSPI_INDEX_TICKER)
    return df


def run_kospi_collection(target_date: date | None = None) -> None:
    """
    KOSPI 전 종목 가격 데이터를 수집해 DB에 저장한다.

    Parameters
    ----------
    target_date : date | None
        수집 기준일. None이면 오늘 날짜 사용.
    """
    today = target_date or date.today()
    # 5년치 + α 확보를 위해 2000일 수집 (최초 실행 시)
    # 이미 데이터가 있으면 최근 7일만 수집 (증분 업데이트)
    # 여기서는 단순하게 target_date 기준 최근 2일 증분으로 설계
    # 초기 풀 수집은 별도 CLI 스크립트로 수행
    start_date = today - timedelta(days=7)

    start_str = start_date.strftime("%Y%m%d")
    end_str = today.strftime("%Y%m%d")

    logger.info("KOSPI 수집 시작: %s ~ %s", start_str, end_str)

    try:
        tickers = _fetch_ticker_list(end_str)
    except Exception:
        logger.exception("KOSPI 티커 목록 조회 실패, 배치 중단")
        return

    logger.info("총 %d개 KOSPI 종목 처리 시작", len(tickers))

    price_records: list[dict] = []
    master_records: list[dict] = []
    failed_tickers: list[str] = []

    for i, ticker in enumerate(tickers):
        try:
            ohlcv = _fetch_ohlcv(start_str, end_str, ticker, adjusted=True)
            cap_df = _fetch_market_cap(start_str, end_str, ticker)

            if ohlcv.empty:
                continue

            # 컬럼 정규화 (pykrx 컬럼명이 한글)
            close_col = "종가" if "종가" in ohlcv.columns else ohlcv.columns[3]
            open_col = "시가" if "시가" in ohlcv.columns else ohlcv.columns[0]
            high_col = "고가" if "고가" in ohlcv.columns else ohlcv.columns[1]
            low_col = "저가" if "저가" in ohlcv.columns else ohlcv.columns[2]
            vol_col = "거래량" if "거래량" in ohlcv.columns else ohlcv.columns[4]

            close_idx = ohlcv.columns.get_loc(close_col) + 1
            open_idx = ohlcv.columns.get_loc(open_col) + 1
            high_idx = ohlcv.columns.get_loc(high_col) + 1
            low_idx = ohlcv.columns.get_loc(low_col) + 1
            vol_idx = ohlcv.columns.get_loc(vol_col) + 1

            cap_col = "시가총액" if "시가총액" in cap_df.columns else cap_df.columns[0]

            master_records.append({
                "ticker": ticker,
                "market": MARKET,
                "name": _fetch_ticker_name_safe(ticker),
                "is_active": True,
            })

            for row in ohlcv.itertuples(index=True, name=None):
                idx_date = row[0]
                cap_val = None
                if not cap_df.empty and idx_date in cap_df.index:
                    cap_val = int(cap_df.loc[idx_date, cap_col])

                price_records.append({
                    "ticker": ticker,
                    "market": MARKET,
                    "date": idx_date.date(),
                    "open": float(row[open_idx]) if pd.notna(row[open_idx]) else None,
                    "high": float(row[high_idx]) if pd.notna(row[high_idx]) else None,
                    "low": float(row[low_idx]) if pd.notna(row[low_idx]) else None,
                    "close_adj": float(row[close_idx]),
                    "volume": int(row[vol_idx]) if pd.notna(row[vol_idx]) else None,
                    "market_cap": cap_val,
                })

            # KRX 서버 부하 방지
            if (i + 1) % 50 == 0:
                time.sleep(0.5)
                logger.info("KOSPI %d/%d 처리 중...", i + 1, len(tickers))

        except Exception:
            logger.warning("KOSPI 종목 %s 수집 실패, 스킵", ticker)
            failed_tickers.append(ticker)
            continue

    # KOSPI 지수 수집
    index_records: list[dict] = []
    try:
        idx_df = _fetch_kospi_index(start_str, end_str)
        close_col = "종가" if "종가" in idx_df.columns else idx_df.columns[3]
        close_idx = idx_df.columns.get_loc(close_col) + 1
        for row in idx_df.itertuples(index=True, name=None):
            idx_date = row[0]
            index_records.append({
                "index_code": INDEX_CODE,
                "date": idx_date.date(),
                "close_adj": float(row[close_idx]),
            })
    except Exception:
        logger.warning("KOSPI 지수 수집 실패")

    # DB 저장
    with SyncSessionLocal() as session:
        if price_records:
            upsert_price_daily_sync(session, price_records)
            logger.info("KOSPI 가격 %d건 저장 완료", len(price_records))
        if index_records:
            upsert_index_daily_sync(session, index_records)
            logger.info("KOSPI 지수 %d건 저장 완료", len(index_records))
        if master_records:
            upsert_securities_master_sync(session, master_records)
            logger.info("KOSPI securities_master %d건 저장 완료", len(master_records))

    if failed_tickers:
        logger.warning("KOSPI 수집 실패 종목 %d개: %s", len(failed_tickers), failed_tickers[:10])

    logger.info("KOSPI 수집 완료")


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


def run_kospi_full_history(start_date: date, end_date: date) -> None:
    """
    초기 풀 히스토리 수집 (CLI로 1회 실행). 이미 데이터가 있는 티커는 스킵.
    """
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    logger.info("KOSPI 풀 히스토리 수집: %s ~ %s", start_str, end_str)

    try:
        all_tickers = _fetch_ticker_list(end_str)
    except Exception:
        logger.exception("KOSPI 티커 목록 조회 실패")
        return

    covered = _get_covered_tickers(MARKET, start_date, end_date)
    tickers = [t for t in all_tickers if t not in covered]
    logger.info(
        "KOSPI: 전체 %d개 중 %d개 스킵(기존 데이터), %d개 수집 예정",
        len(all_tickers), len(covered), len(tickers),
    )

    if not tickers:
        logger.info("모든 KOSPI 티커의 데이터가 이미 존재합니다.")
        return

    price_records: list[dict] = []
    master_records: list[dict] = []
    index_records: list[dict] = []

    for i, ticker in enumerate(tickers):
        try:
            ohlcv = _fetch_ohlcv(start_str, end_str, ticker, adjusted=True)
            cap_df = _fetch_market_cap(start_str, end_str, ticker)

            if ohlcv.empty:
                continue

            master_records.append({
                "ticker": ticker,
                "market": MARKET,
                "name": _fetch_ticker_name_safe(ticker),
                "is_active": True,
            })

            close_col = "종가" if "종가" in ohlcv.columns else ohlcv.columns[3]
            open_col = "시가" if "시가" in ohlcv.columns else ohlcv.columns[0]
            high_col = "고가" if "고가" in ohlcv.columns else ohlcv.columns[1]
            low_col = "저가" if "저가" in ohlcv.columns else ohlcv.columns[2]
            vol_col = "거래량" if "거래량" in ohlcv.columns else ohlcv.columns[4]

            close_idx = ohlcv.columns.get_loc(close_col) + 1
            open_idx = ohlcv.columns.get_loc(open_col) + 1
            high_idx = ohlcv.columns.get_loc(high_col) + 1
            low_idx = ohlcv.columns.get_loc(low_col) + 1
            vol_idx = ohlcv.columns.get_loc(vol_col) + 1
            cap_col = "시가총액" if "시가총액" in cap_df.columns else (cap_df.columns[0] if not cap_df.empty else None)

            for row in ohlcv.itertuples(index=True, name=None):
                idx_date = row[0]
                cap_val = None
                if cap_col and not cap_df.empty and idx_date in cap_df.index:
                    cap_val = int(cap_df.loc[idx_date, cap_col])

                price_records.append({
                    "ticker": ticker,
                    "market": MARKET,
                    "date": idx_date.date(),
                    "open": float(row[open_idx]) if pd.notna(row[open_idx]) else None,
                    "high": float(row[high_idx]) if pd.notna(row[high_idx]) else None,
                    "low": float(row[low_idx]) if pd.notna(row[low_idx]) else None,
                    "close_adj": float(row[close_idx]),
                    "volume": int(row[vol_idx]) if pd.notna(row[vol_idx]) else None,
                    "market_cap": cap_val,
                })

            if (i + 1) % 50 == 0:
                time.sleep(1.0)
                logger.info("KOSPI 풀 수집 %d/%d...", i + 1, len(tickers))

            # 배치 단위로 DB 저장 (메모리 절약)
            if len(price_records) >= 10_000:
                with SyncSessionLocal() as session:
                    upsert_price_daily_sync(session, price_records)
                logger.info("중간 저장: %d건", len(price_records))
                price_records.clear()

        except Exception:
            logger.warning("종목 %s 수집 실패, 스킵", ticker)
            continue

    # 지수
    try:
        idx_df = _fetch_kospi_index(start_str, end_str)
        close_col = "종가" if "종가" in idx_df.columns else idx_df.columns[3]
        close_idx = idx_df.columns.get_loc(close_col) + 1
        for row in idx_df.itertuples(index=True, name=None):
            idx_date = row[0]
            index_records.append({
                "index_code": INDEX_CODE,
                "date": idx_date.date(),
                "close_adj": float(row[close_idx]),
            })
    except Exception:
        logger.warning("KOSPI 지수 풀 수집 실패")

    with SyncSessionLocal() as session:
        if price_records:
            upsert_price_daily_sync(session, price_records)
        if index_records:
            upsert_index_daily_sync(session, index_records)
        if master_records:
            upsert_securities_master_sync(session, master_records)
            logger.info("KOSPI securities_master %d건 저장 완료", len(master_records))

    logger.info("KOSPI 풀 히스토리 수집 완료")

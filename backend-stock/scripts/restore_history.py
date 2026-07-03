"""
price_daily 풀 히스토리 복구 스크립트 (asyncpg 직접 사용).

psycopg2가 Railway 프록시에서 동작하지 않아 asyncpg를 직접 사용.

실행:
    cd backend-stock
    .venv\Scripts\python.exe restore_history.py nasdaq
    .venv\Scripts\python.exe restore_history.py kospi
    .venv\Scripts\python.exe restore_history.py all
    .venv\Scripts\python.exe restore_history.py rankings   # 랭킹만 재계산
"""

import asyncio
import logging
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import asyncpg

# .env 및 .env.prod 파일에서 환경 변수 로드 (KRX_ID, DATABASE_URL 등)
for _env_name in [".env", ".env.prod"]:
    _env_file = Path(__file__).parent / _env_name
    if _env_file.exists():
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())
import pandas as pd

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL is not set in environment or .env.prod")

HISTORY_START = date(2020, 6, 1)
HISTORY_END = date.today()

# ── asyncpg 유틸 ──────────────────────────────────────────────────────────────

async def get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(DB_URL, ssl=False)


async def upsert_price_daily(conn: asyncpg.Connection, records: list[dict]) -> int:
    if not records:
        return 0
    sql = """
        INSERT INTO price_daily (ticker, market, date, open, high, low, close_adj, volume, market_cap)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT ON CONSTRAINT uq_price_daily DO UPDATE SET
          open       = EXCLUDED.open,
          high       = EXCLUDED.high,
          low        = EXCLUDED.low,
          close_adj  = EXCLUDED.close_adj,
          volume     = EXCLUDED.volume,
          market_cap = EXCLUDED.market_cap
    """
    rows = [
        (
            r["ticker"], r["market"], r["date"],
            r.get("open"), r.get("high"), r.get("low"),
            r["close_adj"],
            r.get("volume"), r.get("market_cap"),
        )
        for r in records
    ]
    await conn.executemany(sql, rows)
    return len(rows)


async def upsert_index_daily(conn: asyncpg.Connection, records: list[dict]) -> int:
    if not records:
        return 0
    sql = """
        INSERT INTO index_daily (index_code, date, close_adj)
        VALUES ($1, $2, $3)
        ON CONFLICT ON CONSTRAINT uq_index_daily DO UPDATE SET
          close_adj = EXCLUDED.close_adj
    """
    rows = [(r["index_code"], r["date"], r["close_adj"]) for r in records]
    await conn.executemany(sql, rows)
    return len(rows)


async def upsert_securities_master(conn: asyncpg.Connection, records: list[dict]) -> int:
    if not records:
        return 0
    sql = """
        INSERT INTO securities_master (ticker, market, name, is_active, updated_at)
        VALUES ($1, $2, $3, $4, NOW())
        ON CONFLICT ON CONSTRAINT uq_securities_master DO UPDATE SET
          name       = COALESCE(EXCLUDED.name, securities_master.name),
          is_active  = EXCLUDED.is_active,
          updated_at = NOW()
    """
    rows = [
        (r["ticker"], r["market"], r.get("name"), r.get("is_active", True))
        for r in records
    ]
    await conn.executemany(sql, rows)
    return len(rows)


async def get_covered_tickers(conn: asyncpg.Connection, market: str, start: date, end: date, min_rows: int = 100) -> set[str]:
    """min_rows 이상 데이터가 있는 티커 반환 (스킵 대상)."""
    rows = await conn.fetch(
        "SELECT ticker FROM price_daily "
        "WHERE market=$1 AND date BETWEEN $2 AND $3 "
        "GROUP BY ticker HAVING COUNT(*) >= $4",
        market, start, end, min_rows,
    )
    return {r["ticker"] for r in rows}


# ── NASDAQ 복구 ───────────────────────────────────────────────────────────────

async def restore_nasdaq() -> None:
    from fomobot.batch.collect_nasdaq import (
        fetch_nasdaq_tickers,
        _download_batch,
        _parse_batch_df,
        _fetch_nasdaq_name_map,
    )
    from fomobot.config import settings

    start_str = HISTORY_START.strftime("%Y-%m-%d")
    end_str = (HISTORY_END + timedelta(days=1)).strftime("%Y-%m-%d")

    logger.info("NASDAQ 복구 시작: %s ~ %s", start_str, end_str)

    conn = await get_conn()
    try:
        covered = await get_covered_tickers(conn, "nasdaq", HISTORY_START, HISTORY_END)
        all_tickers = fetch_nasdaq_tickers()
        name_map = _fetch_nasdaq_name_map()

        tickers = [t for t in all_tickers if t not in covered]
        logger.info(
            "NASDAQ: 전체 %d개 중 %d개 스킵(기존), %d개 수집 예정",
            len(all_tickers), len(covered), len(tickers),
        )

        batch_size = settings.batch_size_nasdaq
        batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
        consecutive_failures = 0
        total_saved = 0

        for idx, batch in enumerate(batches):
            if consecutive_failures >= settings.nasdaq_max_consec_failures:
                logger.warning("서킷브레이커: 30분 대기")
                time.sleep(1800)
                consecutive_failures = 0

            try:
                df = _download_batch(batch, start_str, end_str)
                records = _parse_batch_df(df, batch, "nasdaq")
                if records:
                    saved = await upsert_price_daily(conn, records)
                    total_saved += saved
                consecutive_failures = 0
            except Exception:
                logger.warning("NASDAQ 배치 %d/%d 실패", idx + 1, len(batches))
                consecutive_failures += 1
                continue

            if (idx + 1) % 10 == 0:
                logger.info("NASDAQ 진행: %d/%d 배치, 누적 %d건", idx + 1, len(batches), total_saved)

            time.sleep(settings.nasdaq_batch_delay_sec)

        # QQQ 지수
        try:
            df_qqq = _download_batch(["QQQ"], start_str, end_str)
            if not df_qqq.empty:
                close = df_qqq["Close"] if "Close" in df_qqq.columns else df_qqq["QQQ"]["Close"]
                idx_records = [
                    {"index_code": "QQQ", "date": d.date(), "close_adj": float(v)}
                    for d, v in close.items() if pd.notna(v)
                ]
                saved = await upsert_index_daily(conn, idx_records)
                logger.info("QQQ 지수 %d건 저장", saved)
        except Exception:
            logger.warning("QQQ 지수 수집 실패")

        # securities_master
        master = [{"ticker": t, "market": "nasdaq", "name": name_map.get(t), "is_active": True} for t in all_tickers]
        await upsert_securities_master(conn, master)
        logger.info("NASDAQ securities_master %d건 저장 완료", len(master))
        logger.info("NASDAQ 복구 완료: 총 %d건", total_saved)

    finally:
        await conn.close()


# ── KOSPI 복구 ────────────────────────────────────────────────────────────────

async def restore_kospi() -> None:
    from fomobot.batch.collect_kospi import (
        _fetch_ticker_list,
        _fetch_ohlcv,
        _fetch_market_cap,
        _fetch_ticker_name_safe,
        _fetch_kospi_index,
    )

    start_str = HISTORY_START.strftime("%Y%m%d")
    end_str = HISTORY_END.strftime("%Y%m%d")

    logger.info("KOSPI 복구 시작: %s ~ %s", start_str, end_str)

    conn = await get_conn()
    try:
        covered = await get_covered_tickers(conn, "kospi", HISTORY_START, HISTORY_END)
        all_tickers = _fetch_ticker_list(end_str)
        tickers = [t for t in all_tickers if t not in covered]
        logger.info(
            "KOSPI: 전체 %d개 중 %d개 스킵(기존), %d개 수집 예정",
            len(all_tickers), len(covered), len(tickers),
        )

        price_records: list[dict] = []
        master_records: list[dict] = []
        total_saved = 0

        for i, ticker in enumerate(tickers):
            try:
                ohlcv = _fetch_ohlcv(start_str, end_str, ticker, adjusted=True)
                cap_df = _fetch_market_cap(start_str, end_str, ticker)
                if ohlcv.empty:
                    continue

                close_col = "종가" if "종가" in ohlcv.columns else ohlcv.columns[3]
                open_col  = "시가" if "시가" in ohlcv.columns else ohlcv.columns[0]
                high_col  = "고가" if "고가" in ohlcv.columns else ohlcv.columns[1]
                low_col   = "저가" if "저가" in ohlcv.columns else ohlcv.columns[2]
                vol_col   = "거래량" if "거래량" in ohlcv.columns else ohlcv.columns[4]
                cap_col   = "시가총액" if not cap_df.empty and "시가총액" in cap_df.columns else (cap_df.columns[0] if not cap_df.empty else None)

                master_records.append({"ticker": ticker, "market": "kospi", "name": _fetch_ticker_name_safe(ticker), "is_active": True})

                for idx_date, row in ohlcv.iterrows():
                    cap_val = None
                    if cap_col and not cap_df.empty and idx_date in cap_df.index:
                        cap_val = int(cap_df.loc[idx_date, cap_col])
                    price_records.append({
                        "ticker": ticker, "market": "kospi",
                        "date": idx_date.date(),
                        "open":      float(row[open_col])  if pd.notna(row[open_col])  else None,
                        "high":      float(row[high_col])  if pd.notna(row[high_col])  else None,
                        "low":       float(row[low_col])   if pd.notna(row[low_col])   else None,
                        "close_adj": float(row[close_col]),
                        "volume":    int(row[vol_col])     if pd.notna(row[vol_col])   else None,
                        "market_cap": cap_val,
                    })

                if (i + 1) % 50 == 0:
                    time.sleep(1.0)
                    logger.info("KOSPI 진행: %d/%d 종목", i + 1, len(tickers))

                if len(price_records) >= 10_000:
                    saved = await upsert_price_daily(conn, price_records)
                    total_saved += saved
                    logger.info("중간 저장 %d건 (누적 %d건)", saved, total_saved)
                    price_records.clear()

            except Exception:
                logger.warning("KOSPI 종목 %s 수집 실패, 스킵", ticker)
                continue

        if price_records:
            saved = await upsert_price_daily(conn, price_records)
            total_saved += saved

        # KOSPI 지수
        try:
            idx_df = _fetch_kospi_index(start_str, end_str)
            close_col = "종가" if "종가" in idx_df.columns else idx_df.columns[3]
            idx_records = [
                {"index_code": "KOSPI", "date": d.date(), "close_adj": float(row[close_col])}
                for d, row in idx_df.iterrows()
            ]
            saved = await upsert_index_daily(conn, idx_records)
            logger.info("KOSPI 지수 %d건 저장", saved)
        except Exception:
            logger.warning("KOSPI 지수 수집 실패")

        if master_records:
            await upsert_securities_master(conn, master_records)
            logger.info("KOSPI securities_master %d건 저장 완료", len(master_records))

        logger.info("KOSPI 복구 완료: 총 %d건", total_saved)

    finally:
        await conn.close()


# ── 진입점 ───────────────────────────────────────────────────────────────────
# 랭킹 재계산은 Railway cron(매일 자동 실행) 또는
# Railway 대시보드에서 수동으로 collect 잡을 트리거하면 처리됩니다.

async def main(target: str) -> None:
    if target in ("nasdaq", "all"):
        await restore_nasdaq()
    if target in ("kospi", "all"):
        await restore_kospi()
    logger.info(
        "=== price_daily 복구 완료 ===\n"
        "다음 단계: Railway 대시보드에서 collect 잡을 수동 트리거하거나\n"
        "오늘 저녁 Railway cron이 자동으로 랭킹을 재계산합니다."
    )


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target not in ("nasdaq", "kospi", "all"):
        print("사용법: python restore_history.py [nasdaq|kospi|all]")
        sys.exit(1)
    asyncio.run(main(target))

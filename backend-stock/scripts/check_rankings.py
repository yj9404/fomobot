"""
ranking_snapshot / price_daily 현황 진단 스크립트.

Railway 콘솔 또는 로컬에서 실행:
  python check_rankings.py
"""

import os
import sys
from pathlib import Path

# .env, .env.prod 파일에서 환경 변수 로드
for _env_name in [".env", ".env.prod"]:
    _env_file = Path(__file__).parent / _env_name
    if _env_file.exists():
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

sys.path.insert(0, "src")

import asyncpg
import asyncio
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL is not set in environment or .env.prod")


async def main():
    url = DB_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
    conn = await asyncpg.connect(url, ssl=False)

    print("=" * 60)
    print("1. ranking_snapshot: 마켓별 / 기간별 최신 snapshot_date")
    print("=" * 60)
    rows = await conn.fetch("""
        SELECT market, period, MAX(snapshot_date) as latest_date, COUNT(*) as rows
        FROM ranking_snapshot
        GROUP BY market, period
        ORDER BY market, period
    """)
    for r in rows:
        print(f"  {r['market']:8} {r['period']:8} latest={r['latest_date']}  rows={r['rows']}")

    print()
    print("=" * 60)
    print("2. NASDAQ 각 기간 상위 5종목 (최신 snapshot_date 기준)")
    print("=" * 60)
    for period in ("30d", "90d", "365d", "1825d"):
        rows = await conn.fetch("""
            SELECT rs.period, rs.rank, rs.ticker, rs.name, rs.return_pct, rs.market_cap, rs.snapshot_date
            FROM ranking_snapshot rs
            WHERE rs.market = 'nasdaq' AND rs.period = $1
              AND rs.snapshot_date = (
                  SELECT MAX(snapshot_date) FROM ranking_snapshot
                  WHERE market = 'nasdaq' AND period = $1
              )
            ORDER BY rs.rank
            LIMIT 5
        """, period)
        print(f"\n  [nasdaq {period}]")
        for r in rows:
            cap_b = f"${r['market_cap']/1e9:.1f}B" if r['market_cap'] else "N/A"
            print(f"    #{r['rank']:3}  {r['ticker']:8}  {r['return_pct']:8.1f}%  cap={cap_b}  as_of={r['snapshot_date']}")

    print()
    print("=" * 60)
    print("3. KOSPI 각 기간 상위 5종목 (최신 snapshot_date 기준)")
    print("=" * 60)
    for period in ("30d", "90d", "365d", "1825d"):
        rows = await conn.fetch("""
            SELECT rs.period, rs.rank, rs.ticker, rs.name, rs.return_pct, rs.market_cap, rs.snapshot_date
            FROM ranking_snapshot rs
            WHERE rs.market = 'kospi' AND rs.period = $1
              AND rs.snapshot_date = (
                  SELECT MAX(snapshot_date) FROM ranking_snapshot
                  WHERE market = 'kospi' AND period = $1
              )
            ORDER BY rs.rank
            LIMIT 5
        """, period)
        print(f"\n  [kospi {period}]")
        for r in rows:
            cap_b = f"₩{r['market_cap']/1e12:.2f}T" if r['market_cap'] else "N/A"
            print(f"    #{r['rank']:3}  {r['ticker']:8}  {r['return_pct']:8.1f}%  cap={cap_b}  as_of={r['snapshot_date']}")

    print()
    print("=" * 60)
    print("4. NASDAQ price_daily: 날짜별 티커 수 분포 (기간 커버리지 확인)")
    print("=" * 60)
    rows = await conn.fetch("""
        SELECT
            CASE
                WHEN date >= '2026-04-03' THEN '90d_range (>=2026-04-03)'
                WHEN date >= '2025-07-02' THEN '365d_range (>=2025-07-02)'
                WHEN date >= '2021-07-02' THEN '1825d_range (>=2021-07-02)'
                ELSE 'older'
            END as bucket,
            COUNT(DISTINCT ticker) as tickers,
            COUNT(*) as rows,
            MIN(date) as min_date,
            MAX(date) as max_date
        FROM price_daily
        WHERE market = 'nasdaq'
        GROUP BY 1
        ORDER BY min_date
    """)
    for r in rows:
        print(f"  {r['bucket']:35}  tickers={r['tickers']:5}  rows={r['rows']:8}  {r['min_date']} ~ {r['max_date']}")

    print()
    print("=" * 60)
    print("5. NASDAQ price_daily: REPL 날짜 범위 (상위 랭킹 종목 확인)")
    print("=" * 60)
    for ticker in ("REPL", "BLZE", "HQ", "NVCT", "RGNX"):
        rows = await conn.fetch("""
            SELECT MIN(date) as min_date, MAX(date) as max_date, COUNT(*) as rows
            FROM price_daily WHERE market='nasdaq' AND ticker=$1
        """, ticker)
        r = rows[0]
        print(f"  {ticker:6}  {r['min_date']} ~ {r['max_date']}  ({r['rows']} rows)")

    print()
    print("=" * 60)
    print("6. NASDAQ price_daily: 전체 날짜 범위 / 티커 수")
    print("=" * 60)
    rows = await conn.fetch("""
        SELECT MIN(date), MAX(date), COUNT(DISTINCT ticker), COUNT(*)
        FROM price_daily WHERE market='nasdaq'
    """)
    r = rows[0]
    print(f"  날짜 범위: {r[0]} ~ {r[1]}")
    print(f"  티커 수: {r[2]},  총 rows: {r[3]}")

    print()
    print("=" * 60)
    print("7. NASDAQ: 2025-07-01 이전 데이터 보유 티커 수")
    print("=" * 60)
    rows = await conn.fetch("""
        SELECT COUNT(DISTINCT ticker) FROM price_daily
        WHERE market='nasdaq' AND date < '2025-07-01'
    """)
    print(f"  365d 이전 데이터 보유 티커 수: {rows[0][0]}")
    rows = await conn.fetch("""
        SELECT COUNT(DISTINCT ticker) FROM price_daily
        WHERE market='nasdaq' AND date < '2021-07-02'
    """)
    print(f"  1825d 이전 데이터 보유 티커 수: {rows[0][0]}")

    await conn.close()


asyncio.run(main())

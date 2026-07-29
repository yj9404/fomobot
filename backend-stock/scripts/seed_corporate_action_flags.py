"""
corporate_action_flag 초기 seed 스크립트.

002070 / 009310 — 소급 정정 불가/미검증 상태로 남은 2종목을 랭킹에서
격리한다. compute_rankings.py가 status in (excluded, pending)인 티커를
읽어 price_matrix에서 제외한다.

실행:
  cd backend-stock
  .venv\\Scripts\\python.exe scripts\\seed_corporate_action_flags.py
"""

import asyncio
import os
import sys
from datetime import date
from pathlib import Path

for _env_name in [".env", ".env.prod"]:
    _env_file = Path(__file__).parent.parent / _env_name
    if _env_file.exists():
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import asyncpg

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL is not set in environment or .env.prod")

SEED_ROWS = [
    {
        "ticker": "002070",
        "market": "kospi",
        "flag_date": date(2026, 7, 29),
        "reason": "new_issuance",
        "status": "excluded",
        "detected_signal": "shares_ratio=30.13 (오차 0.44%, 5종목 중 유일하게 정수 미근접)",
        "note": "05-06 병합 + 05-11 신주발행 중첩, 단일 배수 정정 불가. 소급 스케일 대상 아님.",
    },
    {
        "ticker": "009310",
        "market": "kospi",
        "flag_date": date(2026, 7, 29),
        "reason": "halted",
        "status": "pending",
        "detected_signal": "halt 중 market_cap 기반 shares_ratio=5.0000009 (실거래 미검증)",
        "note": "2026-05-08 병합 추정 factor=5(미검증), 거래정지 지속 중. 재개 후 실거래로 검증 후 정정.",
    },
]

UPSERT_SQL = """
    INSERT INTO corporate_action_flag
        (ticker, market, flag_date, reason, status, detected_signal, note)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT ON CONSTRAINT uq_corporate_action_flag_ticker DO UPDATE SET
        market = EXCLUDED.market,
        flag_date = EXCLUDED.flag_date,
        reason = EXCLUDED.reason,
        status = EXCLUDED.status,
        detected_signal = EXCLUDED.detected_signal,
        note = EXCLUDED.note,
        updated_at = NOW()
"""


async def main():
    url = DB_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
    url = url.split("?", 1)[0]  # ?ssl=disable 등 쿼리스트링은 asyncpg가 오인식 — 대신 ssl=False로 명시
    conn = await asyncpg.connect(url, ssl=False)
    for row in SEED_ROWS:
        await conn.execute(
            UPSERT_SQL,
            row["ticker"], row["market"], row["flag_date"], row["reason"],
            row["status"], row["detected_signal"], row["note"],
        )
        print(f"seed 완료: {row['ticker']} status={row['status']} reason={row['reason']}")

    rows = await conn.fetch("SELECT ticker, market, reason, status, note FROM corporate_action_flag ORDER BY ticker")
    print("\n현재 corporate_action_flag 전체:")
    for r in rows:
        print(f"  {r['ticker']:8} {r['market']:6} {r['reason']:16} {r['status']:10} {r['note']}")

    await conn.close()


asyncio.run(main())

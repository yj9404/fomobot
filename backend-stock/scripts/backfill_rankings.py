"""
과거 날짜 랭킹 스냅샷 백필 스크립트 (1회 실행).

이미 존재하는 날짜는 스킵하므로 중간에 끊겨도 재실행 가능.

사용법:
    python scripts/backfill_rankings.py --market kospi --years 6 --freq weekly
    python scripts/backfill_rankings.py --market nasdaq --years 6 --freq monthly
    python scripts/backfill_rankings.py --market all --years 6 --freq weekly
    python scripts/backfill_rankings.py --market all --years 1 --freq daily
"""

import argparse
import logging
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

FREQ_DAYS = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
}


def get_existing_dates(market: str) -> set[date]:
    """DB에 이미 존재하는 snapshot_date 목록을 반환한다."""
    from sqlalchemy import text
    from fomobot.db.session import SyncSessionLocal

    with SyncSessionLocal() as session:
        rows = session.execute(
            text(
                "SELECT DISTINCT snapshot_date FROM ranking_snapshot "
                "WHERE market = :market"
            ),
            {"market": market},
        ).fetchall()
    return {r[0] for r in rows}


def generate_dates(start: date, end: date, step_days: int) -> list[date]:
    """start ~ end 사이를 step_days 간격으로 나열 (주말 제외, 역순)."""
    dates = []
    cur = end
    while cur >= start:
        # 토(5)·일(6) 제외
        if cur.weekday() < 5:
            dates.append(cur)
        cur -= timedelta(days=step_days)
    return dates


def main():
    parser = argparse.ArgumentParser(description="FomoBot 랭킹 스냅샷 백필")
    parser.add_argument("--market", choices=["kospi", "nasdaq", "all"], default="all")
    parser.add_argument("--years", type=int, default=6, help="백필 기간 (년)")
    parser.add_argument(
        "--freq",
        choices=["daily", "weekly", "monthly"],
        default="weekly",
        help="스냅샷 생성 주기",
    )
    args = parser.parse_args()

    end_date = date.today()
    start_date = end_date - timedelta(days=args.years * 365)
    step = FREQ_DAYS[args.freq]

    markets = ["kospi", "nasdaq"] if args.market == "all" else [args.market]

    from fomobot.batch.compute_rankings import compute_rankings_for_market

    for market in markets:
        existing = get_existing_dates(market)
        dates = generate_dates(start_date, end_date, step)
        todo = [d for d in dates if d not in existing]

        logger.info(
            "%s: 총 %d개 날짜 중 %d개 스킵(기존), %d개 처리 예정",
            market.upper(), len(dates), len(existing & set(dates)), len(todo),
        )

        for i, snapshot_date in enumerate(todo, 1):
            try:
                count = compute_rankings_for_market(market, snapshot_date)
                logger.info(
                    "[%d/%d] %s %s → %d건 저장",
                    i, len(todo), market.upper(), snapshot_date, count,
                )
            except Exception:
                logger.exception(
                    "[%d/%d] %s %s 실패, 다음 날짜로 이동",
                    i, len(todo), market.upper(), snapshot_date,
                )

        logger.info("%s 백필 완료", market.upper())


if __name__ == "__main__":
    main()

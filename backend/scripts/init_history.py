"""
초기 풀 히스토리 수집 CLI 스크립트 (1회 실행).

사용법:
    uv run python scripts/init_history.py --market kospi --years 6
    uv run python scripts/init_history.py --market nasdaq --years 6
    uv run python scripts/init_history.py --market all --years 6
"""

import argparse
import logging
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="FomoBot 초기 히스토리 수집")
    parser.add_argument(
        "--market", choices=["kospi", "nasdaq", "all"], default="all"
    )
    parser.add_argument("--years", type=int, default=6, help="수집 기간 (년)")
    args = parser.parse_args()

    end_date = date.today()
    start_date = end_date - timedelta(days=args.years * 365)

    print(f"수집 기간: {start_date} ~ {end_date}")
    print("주의: 수백만 건 데이터 수집 — 수시간 소요될 수 있음")

    if args.market in ("kospi", "all"):
        from fomobot.batch.collect_kospi import run_kospi_full_history
        print("=== KOSPI 풀 히스토리 수집 시작 ===")
        run_kospi_full_history(start_date, end_date)

    if args.market in ("nasdaq", "all"):
        from fomobot.batch.collect_nasdaq import run_nasdaq_full_history
        print("=== NASDAQ 풀 히스토리 수집 시작 ===")
        run_nasdaq_full_history(start_date, end_date)

    print("완료")


if __name__ == "__main__":
    main()

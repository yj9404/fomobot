"""
랭킹 스냅샷 재배치 스크립트.

기존 데이터(order_dir 컬럼 없음)를 삭제하고 desc/asc 양방향으로 재생성한다.

실행 전 체크리스트:
  1. alembic upgrade head 완료 (order_dir 컬럼 추가됨)
  2. 기존 데이터 삭제:
       DELETE FROM ranking_snapshot WHERE order_dir = 'desc'
         AND snapshot_date < 'YYYY-MM-DD';  -- 재배치 시작 날짜 이전
     또는 전체 삭제:
       TRUNCATE ranking_snapshot;
  3. 이 스크립트 실행

재배치 범위:
  - 최근 90일: 일별 (오늘부터 역산)
  - 91~365일: 주별 (월요일 기준)
  총 약 130개 snapshot_date × KOSPI + NASDAQ

실행 방법:
  cd backend-stock
  DATABASE_URL_SYNC=<sync_url> .venv/Scripts/python.exe backfill_rankings.py

  또는 .env.prod의 DATABASE_URL(asyncpg)을 DATABASE_URL에 설정 후:
  .venv/Scripts/python.exe backfill_rankings.py

  --dry-run 플래그로 실제 저장 없이 날짜 목록만 출력:
  .venv/Scripts/python.exe backfill_rankings.py --dry-run

  특정 날짜 1개만:
  .venv/Scripts/python.exe backfill_rankings.py --date 2026-06-01
"""

import argparse
import logging
import os
import re
import sys
import time
from datetime import date, timedelta

# DATABASE_URL을 .env.prod에서 읽기 (환경변수 미설정 시)
_env_prod = os.path.join(os.path.dirname(__file__), ".env.prod")
if os.path.exists(_env_prod) and "DATABASE_URL" not in os.environ:
    with open(_env_prod, encoding="utf-8") as _f:
        for _line in _f:
            _m = re.match(r'^DATABASE_URL=(.+)', _line.strip())
            if _m:
                os.environ["DATABASE_URL"] = _m.group(1)
                break
if "DATABASE_URL_SYNC" not in os.environ and "DATABASE_URL" in os.environ:
    _url = os.environ["DATABASE_URL"]
    os.environ["DATABASE_URL_SYNC"] = (
        _url.replace("+asyncpg://", "+psycopg2://")
            .replace("postgresql://", "postgresql+psycopg2://")
    )

from fomobot.batch.compute_rankings import compute_rankings_for_market  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _build_dates(today: date) -> list[date]:
    """재배치 대상 날짜 목록 생성.

    - 최근 90일: 일별
    - 91~365일: 주별 (월요일)
    """
    dates: list[date] = []

    # 최근 90일 일별 (오늘 포함)
    for i in range(90):
        dates.append(today - timedelta(days=i))

    # 91~365일 주별 (월요일 기준)
    d = today - timedelta(days=91)
    cutoff = today - timedelta(days=365)
    while d >= cutoff:
        # 해당 주의 월요일
        monday = d - timedelta(days=d.weekday())
        if monday not in dates and monday >= cutoff:
            dates.append(monday)
        d -= timedelta(days=7)

    return sorted(dates)


def main() -> None:
    parser = argparse.ArgumentParser(description="랭킹 스냅샷 재배치")
    parser.add_argument("--dry-run", action="store_true", help="날짜 목록만 출력, 저장 안 함")
    parser.add_argument("--date", help="특정 날짜 1개만 실행 (YYYY-MM-DD)")
    parser.add_argument(
        "--market", choices=["kospi", "nasdaq", "both"], default="both",
        help="실행할 마켓 (기본: both)",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="날짜별 실행 간격(초). 너무 빠르면 DB 부하 발생 (기본: 1.0)",
    )
    args = parser.parse_args()

    today = date.today()

    if args.date:
        target_dates = [date.fromisoformat(args.date)]
    else:
        target_dates = _build_dates(today)

    markets = ["kospi", "nasdaq"] if args.market == "both" else [args.market]

    logger.info(
        "재배치 범위: %d개 날짜 × %s  (dry_run=%s)",
        len(target_dates), markets, args.dry_run,
    )
    logger.info("날짜 범위: %s ~ %s", target_dates[0], target_dates[-1])

    if args.dry_run:
        for d in target_dates:
            print(d)
        return

    total_records = 0
    failed: list[tuple[str, date, str]] = []

    for i, snap_date in enumerate(target_dates, 1):
        for market in markets:
            try:
                n = compute_rankings_for_market(market, snap_date)
                total_records += n
                logger.info(
                    "[%d/%d] %s %s → %d건 저장",
                    i, len(target_dates), market, snap_date, n,
                )
            except Exception as exc:
                logger.error("실패: %s %s — %s", market, snap_date, exc)
                failed.append((market, snap_date, str(exc)))

        if i < len(target_dates):
            time.sleep(args.delay)

    logger.info("완료: 총 %d건 저장, 실패 %d건", total_records, len(failed))
    if failed:
        logger.warning("실패 목록:")
        for market, d, err in failed:
            logger.warning("  %s %s: %s", market, d, err)
        sys.exit(1)


if __name__ == "__main__":
    main()

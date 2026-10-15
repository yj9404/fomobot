"""
KOSPI 다일 수집 공백 복구 스크립트 (1회성).

정기 cron(fomobot.jobs.collect)은 최근 7일만 재수집하고, gap-fill cron은
"고립된 단일 거래일 랭킹 구멍"만 채운다. KRX 로그인 장애처럼 수집 자체가
여러 날 실패한 경우는 둘 다 복구하지 못하므로 이 스크립트로 한 번에 메운다.

순서:
  1. price_daily / index_daily 재수집 — start ~ end를 단일 pykrx 호출 구간으로
     수집한다(adjusted=True가 구간 내에서 일관된 기준으로 맞춰지도록 쪼개지 않음).
  2. 구간 내 실제 거래일마다 랭킹 스냅샷 + breadth 재계산 (둘 다 upsert라 재실행 안전).
  3. corporate action 후보 탐지를 공백 전체로 넓혀 1회 실행 — 정기 cron은
     lookback 7일이라 공백 기간의 액면분할·병합을 보지 못했다. 알림(출력)만, DB write 없음.

실행 전제:
  - 오늘자 cron-kospi / cron-kospi-gapfill 실행이 끝난 뒤 실행할 것.
    KRX는 중복 로그인 시 기존 세션을 끊으므로(pykrx skipDup) 동시 실행 금지.
  - KRX_ID / KRX_PW / DATABASE_URL 환경변수가 있는 Railway 서비스 셸에서 실행.

사용법 (Railway 콘솔/셸):
    cd backend-stock
    python scripts/backfill_kospi_gap.py --start 2026-09-22 --end 2026-10-14
    python scripts/backfill_kospi_gap.py --start 2026-09-22 --end 2026-10-14 --skip-collect   # 2~3단계만

  장중(09:00~15:30 KST)에 실행할 때는 --end를 전 거래일로 지정할 것 —
  오늘을 포함하면 미확정 장중 가격이 저장된다(당일 18:00 cron이 덮어쓰긴 함).
"""

import argparse
import logging
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill_kospi_gap")

MARKET = "kospi"


def _trading_days(start: date, end: date) -> list[date]:
    from fomobot.db.session import SyncSessionLocal

    with SyncSessionLocal() as session:
        rows = session.execute(
            text(
                "SELECT DISTINCT date FROM price_daily "
                "WHERE market = :market AND date BETWEEN :start AND :end ORDER BY date"
            ),
            {"market": MARKET, "start": start, "end": end},
        ).fetchall()
    return [r[0] for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="KOSPI 다일 수집 공백 복구")
    parser.add_argument("--start", type=date.fromisoformat, required=True,
                        help="복구 시작일 (YYYY-MM-DD, 마지막 정상 수집일 권장)")
    parser.add_argument("--end", type=date.fromisoformat, default=date.today(),
                        help="복구 종료일 (기본: 오늘)")
    parser.add_argument("--skip-collect", action="store_true",
                        help="가격 재수집을 건너뛰고 랭킹/breadth/감지만 실행")
    args = parser.parse_args()

    if args.start > args.end:
        parser.error("--start가 --end보다 늦습니다")

    span_days = (args.end - args.start).days

    # 1. 가격 재수집
    if not args.skip_collect:
        from fomobot.batch.collect_kospi import run_kospi_collection

        logger.info("[1/3] 가격 재수집: %s ~ %s (%d일)", args.start, args.end, span_days)
        run_kospi_collection(target_date=args.end, lookback_days=span_days)

    # 2. 거래일별 랭킹 + breadth
    from fomobot.batch.compute_breadth import compute_market_breadth
    from fomobot.batch.compute_rankings import compute_rankings_for_market

    days = _trading_days(args.start, args.end)
    logger.info("[2/3] 랭킹/breadth 재계산: 거래일 %d개 %s", len(days), [d.isoformat() for d in days])

    failed: list[date] = []
    for i, d in enumerate(days, 1):
        try:
            count = compute_rankings_for_market(MARKET, snapshot_date=d)
            compute_market_breadth(MARKET, target_date=d)
            logger.info("[%d/%d] %s 랭킹 %d건", i, len(days), d, count)
        except Exception:
            logger.exception("[%d/%d] %s 실패, 다음 날짜로 이동", i, len(days), d)
            failed.append(d)

    # 3. corporate action 후보 탐지 (공백 전체 + 경계 여유)
    from fomobot.batch.detect_corporate_actions import detect_corporate_actions

    lookback = (date.today() - args.start).days + 7
    logger.info("[3/3] corporate action 후보 탐지 (최근 %d일)", lookback)
    result = detect_corporate_actions(MARKET, lookback_days=lookback)
    for c in result["candidates"]:
        logger.warning(
            "후보: %s signal=%s price_ratio=%.4f reason추정=%s halt인접=%s (%s)",
            c["ticker"], c["signal_type"], c["price_ratio"],
            c["reason_guess"], c["halt_adjacent"], c["detected_signal"],
        )
    logger.info(
        "후보 %d건, market_cap 결측 %d/%d종목 (coverage_alert=%s)",
        len(result["candidates"]), result["market_cap_null_ticker_count"],
        result["checked_ticker_count"], result["market_cap_coverage_alert"],
    )

    if failed:
        logger.error("랭킹/breadth 실패 날짜: %s — --skip-collect로 재실행", failed)
        sys.exit(1)
    logger.info("완료")


if __name__ == "__main__":
    main()

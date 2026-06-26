"""
초기 백필 스크립트.

국토부 실거래가를 2006년부터 현재까지 수도권 시군구×월 단위로 수집한다.
re_collection_log 테이블에 이미 수집(success/empty)된 항목은 자동으로 skip하므로
중단 후 재실행해도 안전하다.

사용 예:
    # 하루 30개 구 처리 (기본)
    python -m realestate.jobs.backfill

    # 처리 구 수 제한
    python -m realestate.jobs.backfill --max-gu 20

    # 특정 시군구만
    python -m realestate.jobs.backfill --sigungu 11680

    # 수집 후 집계·랭킹 계산 건너뜀 (순수 수집만)
    python -m realestate.jobs.backfill --skip-aggregate

국토부 개발계정 트래픽 한도(일 약 10,000회) 대응:
    --max-gu 30 × 약 246개월 ≈ 7,380회/일 → 안전 여유 포함
"""

import argparse
import logging
import sys
import time
from datetime import date

from realestate.batch.collect import collect_sigungu_month
from realestate.batch.regions import SUDOGWON_SIGUNGU
from realestate.config import settings
from realestate.db.crud import get_done_collection_pairs_sync
from realestate.db.session import SyncSessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _generate_year_months(start_ym: str, end_ym: str) -> list[str]:
    """start_ym ~ end_ym 사이의 YYYYMM 목록을 반환한다 (양 끝 포함)."""
    result = []
    year, month = int(start_ym[:4]), int(start_ym[4:])
    end_year, end_month = int(end_ym[:4]), int(end_ym[4:])
    while (year, month) <= (end_year, end_month):
        result.append(f"{year}{month:02d}")
        month += 1
        if month > 12:
            month -= 12
            year += 1
    return result


def _get_end_ym() -> str:
    """백필 종료 년월 = 전전월 (신고 시차 고려)."""
    today = date.today()
    month = today.month - 2
    year = today.year
    if month <= 0:
        month += 12
        year -= 1
    return f"{year}{month:02d}"


def run_backfill(
    max_gu: int | None = None,
    sigungu_filter: str | None = None,
    skip_aggregate: bool = False,
) -> None:
    """
    Parameters
    ----------
    max_gu : 이번 실행에서 처리할 최대 시군구 수 (None이면 전체)
    sigungu_filter : 특정 sigungu_code만 처리
    skip_aggregate : True면 수집 후 집계·랭킹 계산 생략
    """
    if not settings.molit_api_key:
        logger.error("MOLIT_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    start_ym = settings.re_backfill_start_year_month
    end_ym = _get_end_ym()
    all_yms = _generate_year_months(start_ym, end_ym)

    logger.info("백필 범위: %s ~ %s (%d개월)", start_ym, end_ym, len(all_yms))

    target_gu = [
        sg for sg in SUDOGWON_SIGUNGU
        if sigungu_filter is None or sg["code"] == sigungu_filter
    ]

    if max_gu and not sigungu_filter:
        # 이미 완료된 구를 후순위로 밀어 아직 미완인 구를 먼저 처리
        def _completion_ratio(sg: dict) -> float:
            with SyncSessionLocal() as session:
                done = get_done_collection_pairs_sync(session, sg["code"])
            return len(done) / len(all_yms) if all_yms else 1.0

        target_gu = sorted(target_gu, key=_completion_ratio)
        target_gu = target_gu[:max_gu]

    logger.info("처리 대상 시군구: %d개", len(target_gu))

    total_api_calls = 0
    collected_gu: list[str] = []

    for sg in target_gu:
        code = sg["code"]
        name = sg["name"]

        with SyncSessionLocal() as session:
            done_yms = get_done_collection_pairs_sync(session, code)

        pending_yms = [ym for ym in all_yms if ym not in done_yms]

        if not pending_yms:
            logger.info("%s (%s): 이미 완료됨, 스킵", name, code)
            continue

        logger.info("%s (%s): %d/%d개월 수집 시작", name, code, len(pending_yms), len(all_yms))
        gu_calls = 0

        for ym in pending_yms:
            try:
                collect_sigungu_month(code, name, ym)
                gu_calls += 1
                total_api_calls += 1
                time.sleep(settings.re_api_call_delay_sec)
            except Exception:
                logger.exception("%s %s 수집 중 예외 — 다음 년월로 계속", code, ym)

        logger.info("%s: %d회 API 호출 완료", name, gu_calls)
        collected_gu.append(code)

    logger.info("백필 1회 실행 완료: %d개 시군구, 총 %d회 API 호출", len(collected_gu), total_api_calls)

    if not skip_aggregate and collected_gu:
        logger.info("단지 집계 시작 (처리된 시군구: %d개)", len(collected_gu))
        from realestate.batch.complex_aggregate import aggregate_sigungu_complex
        for code in collected_gu:
            try:
                aggregate_sigungu_complex(code, all_yms)
            except Exception:
                logger.exception("%s 단지 집계 중 오류", code)

        logger.info("단지 랭킹 계산 시작")
        from realestate.batch.complex_rankings import compute_complex_rankings
        try:
            compute_complex_rankings()
        except Exception:
            logger.exception("단지 랭킹 계산 중 오류")

    logger.info("백필 완료")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="부동산 초기 백필")
    parser.add_argument("--max-gu", type=int, default=settings.re_backfill_max_gu_per_run,
                        help="이번 실행에서 처리할 최대 시군구 수")
    parser.add_argument("--sigungu", type=str, default=None,
                        help="특정 시군구 코드만 처리 (5자리)")
    parser.add_argument("--skip-aggregate", action="store_true",
                        help="수집 후 집계·랭킹 계산 건너뜀")
    args = parser.parse_args()

    run_backfill(
        max_gu=args.max_gu,
        sigungu_filter=args.sigungu,
        skip_aggregate=args.skip_aggregate,
    )

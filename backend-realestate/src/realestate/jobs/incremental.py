"""
증분 수집 잡 — Railway Cron 또는 APScheduler에서 매월 실행.

최근 N개월(기본 3)을 재수집해 신고 지연 거래를 보정한다.
re_collection_log의 기존 레코드를 덮어쓰고 재집계한다.

Railway Cron 명령:
    python -m realestate.jobs.incremental
"""

import logging
import sys
import time
from datetime import date

from realestate.batch.aggregate import aggregate_sigungu
from realestate.batch.collect import collect_sigungu_month
from realestate.batch.compute_rankings import compute_all_rankings
from realestate.batch.regions import SUDOGWON_SIGUNGU
from realestate.config import settings
from realestate.db.crud import upsert_collection_log_sync
from realestate.db.session import SyncSessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _recent_year_months(n_months: int = 3) -> list[str]:
    today = date.today()
    result = []
    year, month = today.year, today.month
    for _ in range(n_months):
        result.append(f"{year}{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return result


def _force_reset_collection_log(sigungu_code: str, deal_yms: list[str]) -> None:
    """재수집을 위해 해당 항목의 수집 로그를 삭제(재설정)한다."""
    from sqlalchemy import text
    with SyncSessionLocal() as session:
        ym_list = ", ".join(f"'{ym}'" for ym in deal_yms)
        session.execute(
            text(f"""
                DELETE FROM re_collection_log
                WHERE sigungu_code = :code AND deal_ym IN ({ym_list})
            """),
            {"code": sigungu_code},
        )
        session.commit()


def run_incremental(n_months: int = 3) -> None:
    """
    Parameters
    ----------
    n_months : 재수집할 최근 개월 수 (기본 3)
    """
    if not settings.molit_api_key:
        logger.error("MOLIT_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    recent_yms = _recent_year_months(n_months)
    logger.info("증분 수집 시작: 최근 %d개월 %s", n_months, recent_yms)

    for sg in SUDOGWON_SIGUNGU:
        code, name = sg["code"], sg["name"]

        # 강제 재수집을 위해 기존 로그 삭제
        _force_reset_collection_log(code, recent_yms)

        for ym in recent_yms:
            try:
                collect_sigungu_month(code, name, ym)
                time.sleep(settings.re_api_call_delay_sec)
            except Exception:
                logger.exception("%s %s 증분 수집 실패", code, ym)

        try:
            aggregate_sigungu(code, recent_yms)
        except Exception:
            logger.exception("%s 집계 중 오류", code)

    logger.info("랭킹 재계산 시작")
    try:
        compute_all_rankings()
    except Exception:
        logger.exception("랭킹 계산 중 오류")

    logger.info("증분 수집 완료")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="부동산 증분 수집")
    parser.add_argument("--months", type=int, default=3, help="재수집 개월 수 (기본 3)")
    args = parser.parse_args()
    run_incremental(args.months)

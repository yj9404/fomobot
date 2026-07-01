"""
Railway Cron 진입점 — price_daily retention 정리 잡.

오래된 price_daily 행을 삭제해 DB 용량을 유지한다.
백테스트는 오늘(최신) 주가만 price_daily에서 조회하므로
PRICE_DAILY_RETENTION_DAYS 이전 데이터는 불필요하다.

사용법:
    python -m fomobot.jobs.cleanup_price_daily

Railway Cron 설정 예시 (UTC):
    0 3 * * *   → 매일 03:00 UTC (12:00 KST)
    수집 배치(09:00, 21:30 UTC)와 겹치지 않는 시간대 선택.

주의:
    - ranking_snapshot backfill이 완료된 후에 Cron 등록할 것.
    - 삭제 전 검증 쿼리(implementation_plan 참조)로 missing = 0 확인 필요.
"""

import logging
import sys
from datetime import date, timedelta

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from fomobot.sentry_init import init_sentry
init_sentry()


def run() -> None:
    """
    price_daily에서 retention 기간 이전 레코드를 삭제한다.

    삭제 기준: CURRENT_DATE - price_daily_retention_days 이전 날짜.
    VACUUM ANALYZE는 별도로 수동 실행하거나 PostgreSQL autovacuum에 위임.
    """
    from fomobot.config import settings
    from fomobot.db.session import SyncSessionLocal
    from sqlalchemy import text

    cutoff = date.today() - timedelta(days=settings.price_daily_retention_days)
    logger.info(
        "price_daily retention 정리 시작 (기준일: %s, 삭제 대상: %s 이전)",
        date.today(),
        cutoff,
    )

    try:
        with SyncSessionLocal() as session:
            result = session.execute(
                text("DELETE FROM price_daily WHERE date < :cutoff"),
                {"cutoff": cutoff},
            )
            deleted = result.rowcount
            session.commit()

        logger.info("price_daily retention 완료: %d행 삭제 (기준 %d일)", deleted, settings.price_daily_retention_days)

        if deleted == 0:
            logger.info("삭제된 행 없음 — 이미 최신 상태이거나 데이터 없음")

    except Exception:
        logger.exception("price_daily retention 중 예외 발생")
        try:
            import sentry_sdk
            sentry_sdk.capture_exception()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    run()

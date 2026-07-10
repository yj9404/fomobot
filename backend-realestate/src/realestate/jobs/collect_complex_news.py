"""
Railway Cron 진입점 — 단지 관련 뉴스 배치.

랭킹 배치(매월 15일)와 완전히 독립된 주기(주 1회)로 실행된다.

사용법:
    python -m realestate.jobs.collect_complex_news

Railway Cron 설정 (UTC 기준):
    Schedule : 0 18 * * 1
    (매주 월요일 03:00 KST = 전주 일요일 18:00 UTC.)
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from realestate.sentry_init import init_sentry
init_sentry()


def run() -> None:
    from realestate.batch.collect_news import collect_complex_news

    logger.info("=== 단지 뉴스 배치 시작 ===")
    try:
        updated = collect_complex_news()
    except Exception:
        logger.exception("단지 뉴스 배치 중 예외 발생")
        try:
            import sentry_sdk
            sentry_sdk.capture_exception()
        except Exception:
            pass
        sys.exit(1)

    logger.info("단지 뉴스 배치 완료: %d단지 갱신", updated)


if __name__ == "__main__":
    run()

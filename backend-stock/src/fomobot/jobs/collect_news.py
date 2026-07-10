"""
Railway Cron 진입점 — KOSPI 종목 뉴스 배치.

사용법:
    python -m fomobot.jobs.collect_news

Railway Cron 설정 (UTC 기준):
    Schedule : 20 9 * * 1-6
    (09:20 UTC = 18:20 KST. cron-kospi(09:00 UTC = 18:00 KST) 20분 뒤 실행 —
     랭킹 배치가 끝난 뒤 뉴스 배치가 돌도록 버퍼를 둠.)
"""

import logging
import sys

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Sentry는 가장 먼저 초기화 — 이후 발생하는 예외를 모두 캡처
from fomobot.sentry_init import init_sentry
init_sentry()


def run() -> None:
    from fomobot.batch.collect_news import collect_kospi_news

    logger.info("=== KOSPI 뉴스 배치 시작 ===")
    try:
        updated = collect_kospi_news()
    except Exception:
        logger.exception("KOSPI 뉴스 배치 중 예외 발생")
        try:
            import sentry_sdk
            sentry_sdk.capture_exception()
        except Exception:
            pass
        sys.exit(1)

    logger.info("KOSPI 뉴스 배치 완료: %d종목 갱신", updated)


if __name__ == "__main__":
    run()

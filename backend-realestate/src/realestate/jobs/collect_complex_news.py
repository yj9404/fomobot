"""
Railway Cron 진입점 — 동/구 지역 관련 뉴스 배치.

랭킹 배치(매월 15일)와 완전히 독립된 주기(주 1회)로 실행된다.

사용법:
    python -m realestate.jobs.collect_complex_news

Railway Cron 설정 (UTC 기준):
    Schedule : 0 18 * * 1
    (매주 월요일 03:00 KST = 전주 일요일 18:00 UTC.)

모듈 경로는 예전 이름(collect_complex_news)을 그대로 유지한다 — Railway
Dashboard에 등록된 Cron Command 문자열을 바꾸지 않기 위함(내부 로직은
동/구 지역 단위로 전환됨, batch/collect_news.py 참조).
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
    from realestate.batch.collect_news import collect_region_news

    logger.info("=== 지역 뉴스 배치 시작 ===")
    try:
        updated = collect_region_news()
    except Exception:
        logger.exception("지역 뉴스 배치 중 예외 발생")
        try:
            import sentry_sdk
            sentry_sdk.capture_exception()
        except Exception:
            pass
        sys.exit(1)

    logger.info("지역 뉴스 배치 완료: %d개 동 갱신", updated)


if __name__ == "__main__":
    run()

"""
Railway Cron 진입점 — 웹 서버 import 없이 단독 실행 가능.

사용법:
    python -m fomobot.jobs.collect kospi
    python -m fomobot.jobs.collect nasdaq
    python -m fomobot.jobs.collect all   # kospi → nasdaq 순서로 실행

Railway Cron 설정 (UTC 기준):
    KOSPI:   0 9 * * 1-6   → 09:00 UTC = 18:00 KST
             (KOSPI 장 마감 15:30 KST = 06:30 UTC 기준 +2.5h.
              한국은 서머타임 없으므로 고정 오프셋.)
    NASDAQ: 30 21 * * 1-5  → 21:30 UTC = 다음날 06:30 KST
             (NASDAQ 정규장 마감 16:00 EST = 21:00 UTC 기준 +30분,
              서머타임(EDT) 기준 16:00 EDT = 20:00 UTC 기준 +90분.
              EST/EDT 양쪽에서 모두 마감 이후가 되는 시각을 단일 값으로 선택.
              두 cron 으로 나누지 않아도 계절 무관 안전하게 마감 후 실행.)
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


def _collect_kospi() -> int:
    """KOSPI 수집 후 저장된 레코드 수를 반환한다."""
    from fomobot.batch.collect_kospi import run_kospi_collection
    logger.info("=== KOSPI 수집 시작 ===")
    result = run_kospi_collection()
    # run_kospi_collection 은 내부에서 저장까지 완료 후 반환
    # 반환값이 없으므로 0 반환 (로그로 건수 확인)
    return 0


def _collect_nasdaq() -> int:
    """NASDAQ 수집 후 저장된 레코드 수를 반환한다."""
    from fomobot.batch.collect_nasdaq import run_nasdaq_collection
    logger.info("=== NASDAQ 수집 시작 ===")
    run_nasdaq_collection()
    return 0


def _compute_rankings(market: str) -> int:
    """랭킹 계산 후 저장된 스냅샷 수를 반환한다."""
    from fomobot.batch.compute_rankings import compute_rankings_for_market
    logger.info("=== %s 랭킹 계산 시작 ===", market.upper())
    count = compute_rankings_for_market(market)
    return count or 0


def _compute_breadth(market: str) -> None:
    """
    breadth(상승/하락/보합 종목 수) 집계.

    실패해도 본 수집·랭킹 작업을 실패시키지 않는다 — 예외를 여기서 흡수한다.
    (예: market_breadth_daily 마이그레이션이 아직 적용되지 않은 DB를 만나는
    경우. cron 서비스는 Railway Dashboard에서 Command만 오버라이드해 web
    서비스와 별도 컨테이너로 실행되므로 web 서비스 배포 시 실행되는
    `alembic upgrade head`를 거치지 않는다 — web 재배포 전에 cron이 먼저
    돌면 테이블이 없는 상태로 이 함수가 호출될 수 있다.)
    """
    try:
        from fomobot.batch.compute_breadth import compute_market_breadth
        logger.info("=== %s breadth 계산 시작 ===", market.upper())
        result = compute_market_breadth(market)
        if result:
            logger.info(
                "%s breadth 저장 완료: 상승 %d / 하락 %d / 보합 %d",
                market.upper(), result["advancers"], result["decliners"], result["unchanged"],
            )
    except Exception:
        logger.exception(
            "%s breadth 계산 실패 — 본 수집/랭킹 작업에는 영향 없음(격리됨)", market.upper()
        )
        try:
            import sentry_sdk
            sentry_sdk.capture_exception()
        except Exception:
            pass


def _report_warning(message: str) -> None:
    """'성공했지만 비정상'인 상황을 Sentry 경고로 전송한다."""
    try:
        import sentry_sdk
        sentry_sdk.capture_message(message, level="warning")
    except Exception:
        pass
    logger.warning(message)


def run(market: str) -> None:
    """
    지정한 시장의 수집 → 랭킹 계산 → breadth 계산을 순서대로 실행한다.
    수집·랭킹 예외 발생 시 Sentry 가 자동으로 캡처하고, 프로세스를 exit code 1 로 종료한다.
    breadth 계산 실패는 _compute_breadth 내부에서 흡수되어 exit code에 영향을 주지 않는다.
    """
    if market not in ("kospi", "nasdaq", "all"):
        logger.error("지원하지 않는 시장: %s (kospi|nasdaq|all 중 하나)", market)
        sys.exit(1)

    markets = ["kospi", "nasdaq"] if market == "all" else [market]

    for mkt in markets:
        try:
            if mkt == "kospi":
                _collect_kospi()
            else:
                _collect_nasdaq()
        except Exception:
            logger.exception("%s 수집 중 예외 발생", mkt.upper())
            # Sentry 가 자동 캡처하지만 명시적으로도 전송
            try:
                import sentry_sdk
                sentry_sdk.capture_exception()
            except Exception:
                pass
            sys.exit(1)

        try:
            count = _compute_rankings(mkt)
        except Exception:
            logger.exception("%s 랭킹 계산 중 예외 발생", mkt.upper())
            try:
                import sentry_sdk
                sentry_sdk.capture_exception()
            except Exception:
                pass
            sys.exit(1)

        if count == 0:
            _report_warning(
                f"[{mkt.upper()}] 랭킹 계산 결과 0건 — 수집 데이터 없거나 필터 과다 가능성"
            )
        else:
            logger.info("%s 랭킹 %d건 저장 완료", mkt.upper(), count)

        # breadth 계산은 내부에서 예외를 흡수하므로 여기서는 별도 try/except 불필요.
        _compute_breadth(mkt)

    logger.info("배치 완료: %s", market)


if __name__ == "__main__":
    market_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    run(market_arg)

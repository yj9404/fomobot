"""
Railway Cron 진입점 — 랭킹 스냅샷 gap-fill (self-healing).

정기 수집/랭킹 cron(fomobot.jobs.collect)과 별도 서비스로 분리해 실행한다.
gap-fill이 무겁거나 실패해도 당일 정상 랭킹 계산 흐름에 영향을 주지 않기 위함.

이 배치가 하는 일 = "고립된 단일 거래일 랭킹 구멍"의 사후 자동 복구뿐이다.
연속 다중일 공백은 원리상 자동 복구 대상이 아니며(fomobot.batch.gap_fill의
모듈 docstring 참조) WARNING 로그로 사람에게 넘긴다.

사용법:
    python -m fomobot.jobs.gap_fill kospi
    python -m fomobot.jobs.gap_fill nasdaq
    python -m fomobot.jobs.gap_fill all
    python -m fomobot.jobs.gap_fill all --dry-run   # 계산/저장 없이 "무엇을 채울지"만 로깅

Railway Cron 설정 (UTC 기준, 정기 cron보다 45분 뒤로 여유):
    cron-kospi-gapfill  : 45 9 * * 1-6   (정기 cron-kospi 09:00 UTC + 45분)
    cron-nasdaq-gapfill : 15 22 * * 1-5  (정기 cron-nasdaq 21:30 UTC + 45분)
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


def run(market: str, dry_run: bool = False) -> None:
    from fomobot.batch.gap_fill import run_gap_fill_for_market

    if market not in ("kospi", "nasdaq", "all"):
        logger.error("지원하지 않는 시장: %s (kospi|nasdaq|all 중 하나)", market)
        sys.exit(1)

    markets = ["kospi", "nasdaq"] if market == "all" else [market]

    for mkt in markets:
        try:
            report = run_gap_fill_for_market(mkt, dry_run=dry_run)
            logger.info("%s gap-fill 완료: %s", mkt.upper(), report)
        except Exception:
            logger.exception("%s gap-fill 중 예외 발생", mkt.upper())
            try:
                import sentry_sdk
                sentry_sdk.capture_exception()
            except Exception:
                pass
            sys.exit(1)

    logger.info("gap-fill 배치 완료: %s (dry_run=%s)", market, dry_run)


if __name__ == "__main__":
    args = sys.argv[1:]
    dry_run_flag = "--dry-run" in args
    positional = [a for a in args if a != "--dry-run"]
    market_arg = positional[0] if positional else "all"
    run(market_arg, dry_run=dry_run_flag)

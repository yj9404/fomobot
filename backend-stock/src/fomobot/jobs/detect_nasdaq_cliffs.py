"""
Railway Cron 진입점 — NASDAQ 내부절벽 주간 전수 스캔(무거움, 알림 전용).

정기 수집/랭킹 cron(fomobot.jobs.collect)과 별도 서비스로 분리한다.
5년 윈도우 전 종목을 스캔하는 무거운 작업이라 일일 배치에 넣지 않는다
(가벼운 음수/0 가격 가드는 fomobot.jobs.collect에 이미 편입돼 있다 —
fomobot.batch.detect_nasdaq_quality.detect_nasdaq_negative 참조).

이 배치는 격리 후보를 corporate_action_flag에 자동 insert하지 않는다 —
Sentry 경고 + 로그로만 알린다. 절벽은 실제 급락(뉴스 이벤트)과 오염을
거래량 신호로만 구분하므로 오탐 여지가 있어, 운영 확인 후 자동 insert
전환 여부를 별도로 결정한다(fomobot.batch.detect_nasdaq_quality 모듈
docstring 참조).

사용법:
    python -m fomobot.jobs.detect_nasdaq_cliffs

Railway Cron 설정 (UTC 기준, 주 1회 — 정기 cron-nasdaq과 겹치지 않는 시간대):
    cron-nasdaq-cliffscan : 0 3 * * 0   (매주 일요일 03:00 UTC = 12:00 KST,
                             장 마감/랭킹 계산과 무관한 한가한 시간대)
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


def _report_warning(message: str) -> None:
    try:
        import sentry_sdk
        sentry_sdk.capture_message(message, level="warning")
    except Exception:
        pass
    logger.warning(message)


def run(market: str = "nasdaq") -> None:
    try:
        from fomobot.batch.detect_nasdaq_quality import detect_nasdaq_cliffs

        result = detect_nasdaq_cliffs(market, full_scan=True)

        logger.info(
            "%s 절벽 스캔 완료: 후보행=%d 유지=%d종목 격리후보=%d종목 랙가능=%d종목 억제=%d건",
            market.upper(), result["scanned_candidate_rows"], len(result["keep"]),
            len(result["isolate_candidates"]), len(result["lag_possible"]),
            result["suppressed_count"],
        )

        if result["isolate_candidates"]:
            tickers = [c["ticker"] for c in result["isolate_candidates"]]
            _report_warning(
                f"[{market.upper()}] 절벽 격리후보 {len(tickers)}종목 탐지(자동 격리 안 됨, "
                f"수동 검토 필요): {tickers}"
            )
        if result["lag_possible"]:
            tickers = [c["ticker"] for c in result["lag_possible"]]
            _report_warning(
                f"[{market.upper()}] 최근 절벽 {len(tickers)}종목 — yfinance 소급 랙 가능성, "
                f"재조회 권장(즉시 격리 대상 아님): {tickers}"
            )
    except Exception:
        logger.exception("%s 절벽 스캔 중 예외 발생", market.upper())
        try:
            import sentry_sdk
            sentry_sdk.capture_exception()
        except Exception:
            pass
        sys.exit(1)

    logger.info("절벽 스캔 배치 완료: %s", market)


if __name__ == "__main__":
    market_arg = sys.argv[1] if len(sys.argv) > 1 else "nasdaq"
    run(market_arg)

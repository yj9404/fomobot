"""
Railway Cron 진입점 — NASDAQ 내부절벽 주간 전수 스캔(무거움, 알림 전용).

정기 수집/랭킹 cron(fomobot.jobs.collect)과 별도 서비스로 분리한다.
5년 윈도우 전 종목을 스캔하는 무거운 작업이라 일일 배치에 넣지 않는다
(가벼운 음수/0 가격 가드는 fomobot.jobs.collect에 이미 편입돼 있다 —
fomobot.batch.detect_nasdaq_quality.detect_nasdaq_negative 참조).

격리 후보 중 yfinance 분할 이력으로 역분할이 확인된 종목만
corporate_action_flag에 자동 격리한다(Sentry에 격리 내역 경고). 확인되지
않은 후보는 실제 급등락과 구분할 수 없어 격리하지 않고 Sentry 경고 + 로그로만
알린다(fomobot.batch.detect_nasdaq_quality 모듈 docstring 참조).

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


# Sentry 메시지가 티커 수십 개로 길어지지 않게 상세 표기할 종목 수 (전체는 로그에 남는다)
ALERT_DETAIL_LIMIT = 20


def format_candidates(candidates: list[dict], cliffs_key: str = "isolate_cliffs") -> str:
    """
    후보 종목을 '티커 절벽일 x배율 vol거래량비' 형태로 요약한다 (최근 절벽 순).

    티커 목록만으로는 역분할인지 실제 급락인지 알림만 보고 판단할 수 없어,
    종목당 가장 최근 절벽의 날짜·배율·거래량 비율을 함께 보여준다.
    이미 검토해 corporate_action_flag로 격리한 종목은 다음 스캔부터 후보에서
    빠지므로, 이 목록은 자연히 "아직 처리 안 된 종목"만 남는다.
    """
    rows = []
    for c in candidates:
        last = max(c[cliffs_key], key=lambda x: x["cliff_date"])
        rows.append((last["cliff_date"], c["ticker"], last["ratio"], last["vol_ratio"]))
    rows.sort(reverse=True)

    def fmt(r):
        vol = "inf" if r[3] == float("inf") else f"{r[3]:.1f}"
        return f"{r[1]} {r[0]:%m-%d} x{r[2]:.2f} vol{vol}"

    shown = ", ".join(fmt(r) for r in rows[:ALERT_DETAIL_LIMIT])
    rest = len(rows) - ALERT_DETAIL_LIMIT
    return shown + (f" 외 {rest}종목" if rest > 0 else "")


def run(market: str = "nasdaq") -> None:
    try:
        from fomobot.batch.detect_nasdaq_quality import (
            auto_isolate_reverse_splits,
            detect_nasdaq_cliffs,
        )

        result = detect_nasdaq_cliffs(market, full_scan=True)

        logger.info(
            "%s 절벽 스캔 완료: 후보행=%d 유지=%d종목 격리후보=%d종목 랙가능=%d종목 억제=%d건",
            market.upper(), result["scanned_candidate_rows"], len(result["keep"]),
            len(result["isolate_candidates"]), len(result["lag_possible"]),
            result["suppressed_count"],
        )

        isolated = auto_isolate_reverse_splits(result["isolate_candidates"], market)
        if isolated:
            _report_warning(
                f"[{market.upper()}] 역분할 확인 자동 격리 {len(isolated)}종목: "
                + ", ".join(
                    f"{i['ticker']} 절벽 {i['cliff_date']:%m-%d} x{i['ratio']:.2f} "
                    f"/ 분할 {i['split_date']:%m-%d} ({i['split_ratio']:g})"
                    for i in isolated[:ALERT_DETAIL_LIMIT]
                )
                # 가격을 무인으로 덮어쓰지 않는다 — dry-run으로 판정을 확인한 뒤 사람이 --apply
                + " | 정정: backend-stock에서 scripts/refetch_nasdaq_splits.py 실행(dry-run 확인 후 --apply),"
                " hold된 종목은 scripts/scale_nasdaq_splits.py"
            )
        isolated_tickers = {i["ticker"] for i in isolated}
        remaining = [c for c in result["isolate_candidates"] if c["ticker"] not in isolated_tickers]
        if remaining:
            _report_warning(
                f"[{market.upper()}] 절벽 격리후보 {len(remaining)}종목 탐지(분할 이력 미확인이라 "
                f"자동 격리 안 됨, 수동 검토 필요): {format_candidates(remaining)}"
            )
        if result["lag_possible"]:
            candidates = result["lag_possible"]
            _report_warning(
                f"[{market.upper()}] 최근 절벽 {len(candidates)}종목 — yfinance 소급 랙 가능성, "
                f"재조회 권장(즉시 격리 대상 아님): {format_candidates(candidates)}"
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

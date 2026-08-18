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
    run_kospi_collection()
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


def _run_corporate_action_checks(market: str) -> None:
    """
    corporate action(액면분할·병합) 신규 후보 탐지 + halt 재개 체크.

    이번 단계는 알림만 — corporate_action_flag에 자동 insert하지 않는다
    (오탐률을 몇 주 지켜본 뒤 다음 단계에서 자동 등록 전환 여부 결정).
    실패해도 본 수집/랭킹 작업에는 영향 없다 — _compute_breadth와 동일하게
    예외를 여기서 흡수하고 Sentry로만 올린다(격리).
    """
    try:
        from fomobot.batch.detect_corporate_actions import (
            RESUMPTION_NEXT_STEPS,
            check_halt_resumption,
            detect_corporate_actions,
            detect_long_halts,
        )

        result = detect_corporate_actions(market, lookback_days=7)
        for c in result["candidates"]:
            _report_warning(
                f"[{market.upper()}] corporate action 후보 탐지: {c['ticker']} "
                f"signal={c['signal_type']} price_ratio={c['price_ratio']:.4f} "
                f"reason추정={c['reason_guess']} halt인접={c['halt_adjacent']} "
                f"({c['detected_signal']})"
            )

        # 후보 유무와 무관하게 항상 별도 확인 — "후보 0건"이 "이벤트 없음"인지
        # "market_cap 결측으로 계산 자체가 불가능했음"인지 구분하지 못하면
        # 알림 기반 관찰이 무의미해진다(027970 미탐 사고로 실증됨).
        # KOSPI 한정 — NASDAQ은 price_daily.market_cap이 애초에 전량 NULL이라
        # (detect_nasdaq_quality.py 참조) 이 임계값이 매일 무의미하게 울린다.
        if market == "kospi" and result["market_cap_coverage_alert"]:
            _report_warning(
                f"[{market.upper()}] market_cap 결측 {result['market_cap_null_ticker_count']}"
                f"/{result['checked_ticker_count']}종목 — shares_ratio 신호 계산 불가 구간 존재, "
                f"감지 사각 발생 가능(임계 초과)"
            )

        # 정지 시작 → 자동 pending 등록(여기) → 재개 시 알림(check_halt_resumption) →
        # 사람이 실제 사유 확인해 정정/해제. 가격 점프 데이터를 기다리지 않고
        # "정지 지속 자체"만으로 판정하므로, 위 detect_corporate_actions와 달리
        # 여기서 실제 write까지 일어난다(함수 내부에서 자동 insert).
        long_halts = detect_long_halts(market)
        for h in long_halts:
            _report_warning(
                f"[{market.upper()}] 장기 매매정지 자동 등록: {h['ticker']} "
                f"정지 시작(추정) {h['halt_start_date']}, 연속 {h['halt_trading_days']}거래일 "
                f"— corporate_action_flag(pending/halted) 신규 등록, 랭킹 제외 시작"
            )

        resumptions = check_halt_resumption(market)
        for r in resumptions:
            if r["resumed"]:
                _report_warning(
                    f"[{market.upper()}] {r['ticker']} 거래 재개 감지 — "
                    f"재개 첫 실거래일 {r['last_real_trade_date']}. "
                    f"{RESUMPTION_NEXT_STEPS}"
                )
    except Exception:
        logger.exception(
            "%s corporate action 감지/halt 재개 체크 실패 — 본 수집/랭킹 작업에는 영향 없음(격리됨)",
            market.upper(),
        )
        try:
            import sentry_sdk
            sentry_sdk.capture_exception()
        except Exception:
            pass


def _run_negative_price_guard(market: str) -> None:
    """
    NASDAQ 전용 음수/0 가격 일일 가드(close_adj<=0 자동 격리).

    price_daily WHERE 한 줄만 거는 가벼운 쿼리라 매일 돌려도 부담 없다.
    발견 시 corporate_action_flag에 자동 insert(reason=negative_price,
    status=excluded)까지 이 함수가 수행한다 — 음수는 명백한 오류라
    오탐 여지가 없다(_run_corporate_action_checks의 절벽 후보와 달리
    자동 격리가 안전). 실패해도 본 수집/랭킹 작업에는 영향 없음(격리).
    KOSPI는 대상 아님 — pykrx 수집 경로는 이 문제가 없었다.
    """
    if market != "nasdaq":
        return
    try:
        from fomobot.batch.detect_nasdaq_quality import detect_nasdaq_negative

        results = detect_nasdaq_negative(market)
        for r in results:
            _report_warning(
                f"[{market.upper()}] 음수/0 가격 자동 격리: {r['ticker']} "
                f"{r['count']}건 (최근 {r['last_negative_date']}, "
                f"classification={r['classification']})"
            )
    except Exception:
        logger.exception(
            "%s 음수 가격 가드 실패 — 본 수집/랭킹 작업에는 영향 없음(격리됨)", market.upper()
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

        # corporate action 감지/halt 재개 체크도 내부에서 예외를 흡수한다(알림만, insert 없음).
        _run_corporate_action_checks(mkt)

        # NASDAQ 음수/0 가격 일일 가드 — 발견 시 자동 격리까지 수행(내부에서 예외 흡수).
        _run_negative_price_guard(mkt)

    logger.info("배치 완료: %s", market)


if __name__ == "__main__":
    market_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    run(market_arg)

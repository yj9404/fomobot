"""
장기 거래정지 재개 첫날 판별.

정지 구간(volume=0 10거래일 이상 연속, close_adj 동결) 직후 재개 첫
실거래일에는 가격제한폭(±30%)이 적용되지 않아 1d 등락이 크게 나올 수
있다(002210 +85% 등 — 진단 세션에서 확인, 데이터 오염 아님). 값은 그대로
두고, compute_rankings가 이 판별 결과를 ranking_snapshot.halt_resumption
플래그로 저장해 프론트가 tooltip으로 설명하게 한다.

002210 자체가 이 설계의 사각지대였다: 정지 구간 close_adj가 판정 시점엔
973으로 균일해(len(run_closes)==1) "순수 재개 급등"으로 True 판정됐지만,
사실은 halt 중 1:2 무상감자(973→1946)가 있었고 KRX가 조정가를 사후
소급 게시하면서 판정 근거였던 "동결"이 나중에 깨졌다(027970과 동일한
소급 게시 지연 메커니즘). close_adj 동결 여부만으로는 이런 사후 개정을
원리적으로 잡을 수 없으므로, corporate_action_flag 조회 기반 배제
조건을 추가한다 — flag는 소급 개정에 흔들리지 않는 안정적 근거다.
"""
from datetime import date, timedelta
import logging

from sqlalchemy.orm import Session

from fomobot.db.crud import get_corporate_action_flag_sync, get_price_series_for_tickers_sync

logger = logging.getLogger(__name__)

HALT_MIN_TRADING_DAYS = 10
LOOKBACK_DAYS = 60  # 10거래일 이상의 halt run을 안전하게 담을 여유(주말·공휴일 포함)

# 이 사유로 corporate_action_flag에 등록된 종목은 halt_resumption 판정에서
# 무조건 배제한다 — status(resolved/excluded/pending)는 무관하다. "이미
# 정정됐는가"가 아니라 "그 정지 구간에 자본거래가 있었는가"가 판정 기준.
CAPITAL_ACTION_REASONS = ("capital_reduction", "merge", "split")


def is_prev_day_halt_resumption(
    session: Session, market: str, ticker: str, prev_date: date, snapshot_date: date,
) -> bool:
    """
    (prev_date -> snapshot_date) 1d 등락이 장기 거래정지 재개 아티팩트인지 판별.

    아래 조건을 전부 충족해야 True를 반환한다:
      1) prev_date가 volume=0 이 HALT_MIN_TRADING_DAYS일 이상 연속된 구간의
         마지막 날이다.
      2) 그 구간 내내 close_adj가 완전히 동결돼 있다 — 비동결이면 정지 중
         행정 재산정(구주가/신주가 basis 전환)이 있었다는 뜻이라 corporate
         action 케이스로 간주하고 여기서는 제외한다(corporate_action_flag
         파이프라인이 별도로 담당).
      3) snapshot_date가 그 구간 종료 직후 첫 실거래일(volume>0)이다.
      4) prev_date 자체는 실거래일이 아니다(volume=0).
      5) 그 정지 구간 [halt_start, prev_date] 안에 corporate_action_flag가
         reason=capital_reduction/merge/split으로 등록돼 있지 않다 —
         002210처럼 판정 시점엔 동결(조건 2)로 보였지만 나중에 소급 개정된
         케이스를 잡기 위한 조건. close_adj 동결 여부만으로는 사후 개정을
         원리적으로 감지할 수 없어 flag 조회로 보강한다. status는 무관.

    호출부(compute_rankings_for_market)가 1d period에서 |return_pct|>30%인
    종목에 대해서만 호출하므로, 이 함수 자체에는 등락폭 조건이 없다.
    """
    lookback_start = prev_date - timedelta(days=LOOKBACK_DAYS)
    series = get_price_series_for_tickers_sync(
        session, market, [ticker], lookback_start, snapshot_date
    )
    if len(series) < HALT_MIN_TRADING_DAYS + 1:
        return False

    series = sorted(series, key=lambda r: r["date"])

    if series[-1]["date"] != snapshot_date or series[-2]["date"] != prev_date:
        # 예상한 두 날짜가 시리즈의 마지막 두 행이 아니면(휴장일 스냅 등
        # 예상 밖 케이스) 안전하게 False 처리한다.
        return False
    if not series[-1]["volume"]:
        return False
    if series[-2]["volume"]:
        return False

    run_closes = set()
    run_len = 0
    halt_start_date = prev_date
    for row in reversed(series[:-1]):
        if row["volume"]:
            break
        run_closes.add(row["close_adj"])
        run_len += 1
        halt_start_date = row["date"]

    if run_len < HALT_MIN_TRADING_DAYS:
        return False
    if len(run_closes) != 1:
        return False

    try:
        flag = get_corporate_action_flag_sync(session, market, ticker)
    except Exception:
        # fail-loud: 조회 실패를 조용히 True로 넘기지 않는다 — 잘못된
        # "정상 재개 보증"보다 tooltip 누락(False)이 안전하다.
        logger.exception(
            "%s %s: corporate_action_flag 조회 실패 — halt_resumption 배제 조건 "
            "확인 불가, 안전측(False)으로 처리",
            market, ticker,
        )
        try:
            import sentry_sdk
            sentry_sdk.capture_exception()
        except Exception:
            pass
        return False

    if (
        flag is not None
        and flag["reason"] in CAPITAL_ACTION_REASONS
        and halt_start_date <= flag["flag_date"] <= prev_date
    ):
        return False

    return True

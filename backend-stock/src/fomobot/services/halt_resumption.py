"""
장기 거래정지 재개 첫날 판별.

정지 구간(volume=0 10거래일 이상 연속, close_adj 동결) 직후 재개 첫
실거래일에는 가격제한폭(±30%)이 적용되지 않아 1d 등락이 크게 나올 수
있다(002210 +85% 등 — 진단 세션에서 확인, 데이터 오염 아님). 값은 그대로
두고, compute_rankings가 이 판별 결과를 ranking_snapshot.halt_resumption
플래그로 저장해 프론트가 tooltip으로 설명하게 한다.
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from fomobot.db.crud import get_price_series_for_tickers_sync

HALT_MIN_TRADING_DAYS = 10
LOOKBACK_DAYS = 60  # 10거래일 이상의 halt run을 안전하게 담을 여유(주말·공휴일 포함)


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
    for row in reversed(series[:-1]):
        if row["volume"]:
            break
        run_closes.add(row["close_adj"])
        run_len += 1

    if run_len < HALT_MIN_TRADING_DAYS:
        return False
    if len(run_closes) != 1:
        return False

    return True

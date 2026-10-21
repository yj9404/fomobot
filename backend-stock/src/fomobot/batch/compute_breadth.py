"""
시장 breadth(상승/하락/보합 종목 수) 집계 배치.

수집 크론(collect_kospi/collect_nasdaq) 완료 후 트리거되어
market_breadth_daily에 upsert한다. API는 이 테이블만 조회한다
(요청 시 실시간 계산 금지).
"""

import logging
from datetime import date, timedelta

from fomobot.db.crud import (
    get_breadth_price_pairs_sync,
    get_last_trading_day_sync,
    get_security_names_sync,
    get_trading_days_since_sync,
    upsert_market_breadth_daily_sync,
)
from fomobot.db.session import SyncSessionLocal
from fomobot.services.breadth import classify_breadth, is_excluded_nasdaq_security

logger = logging.getLogger(__name__)


def compute_market_breadth(market: str, target_date: date | None = None) -> dict | None:
    """
    market의 target_date(없으면 최신 거래일) breadth를 계산해 market_breadth_daily에 upsert한다.

    등락 판정은 LAG 윈도우 함수를 쓰지 않고, target_date와 그 직전 거래일
    (get_last_trading_day_sync로 실측)을 ticker 기준 명시적 JOIN으로 비교한다.
    NASDAQ은 securities_master 종목명에 Warrant/Right(s)/Unit(s)이 단어 단위로
    포함된 종목(SPAC 부속증권 추정)을 집계 전 제외한다. KOSPI는 어떤 필터도
    적용하지 않는다(KRX 공식 집계와 대조 완료).

    Returns
    -------
    dict | None : DB에 반영된 집계 결과. target_date에 데이터가 없으면 None.
    """
    with SyncSessionLocal() as session:
        if target_date is None:
            target_date = get_last_trading_day_sync(session, market)
        if target_date is None:
            logger.warning("%s: price_daily에 데이터가 없어 breadth 계산 불가", market.upper())
            return None

        date_prev = get_last_trading_day_sync(
            session, market, as_of=target_date - timedelta(days=1)
        )

        rows = get_breadth_price_pairs_sync(session, market, target_date, date_prev)

        if market == "nasdaq" and rows:
            tickers = [r["ticker"] for r in rows]
            name_map = get_security_names_sync(session, market, tickers)
            before = len(rows)
            rows = [
                r for r in rows
                if not is_excluded_nasdaq_security(name_map.get(r["ticker"]))
            ]
            logger.info(
                "NASDAQ breadth: SPAC 부속증권류 %d개 제외 (%d → %d종목)",
                before - len(rows), before, len(rows),
            )

        pairs = [(r["close_curr"], r["close_prev"]) for r in rows]
        counts = classify_breadth(pairs)
        halted = sum(1 for r in rows if r["volume_curr"] == 0)
        total = counts["advancers"] + counts["decliners"] + counts["unchanged"] + counts["excluded"]

        record = {
            "market": market,
            "date": target_date,
            "advancers": counts["advancers"],
            "decliners": counts["decliners"],
            "unchanged": counts["unchanged"],
            "excluded": counts["excluded"],
            "halted": halted,
            "total": total,
        }
        upsert_market_breadth_daily_sync(session, record)
        logger.info(
            "%s breadth %s: 상승 %d / 하락 %d / 보합 %d / 제외 %d / 거래정지(참고) %d / 총 %d",
            market.upper(), target_date,
            counts["advancers"], counts["decliners"], counts["unchanged"],
            counts["excluded"], halted, total,
        )
        return record


def recompute_market_breadth(market: str, dates: list[date]) -> list[dict]:
    """
    dates 각 날짜의 breadth를 다시 계산해 upsert한다 (오름차순, 날짜별 실패 격리).

    수집이 이번 실행에서 쓴 날짜를 그대로 받아 쓴다 — 최신일 하루만 계산하면
    여러 날을 따라잡은 날(KOSPI 장애 복구)의 중간 날짜가 비고, 수집이 과거 날짜를
    다시 채운 경우(NASDAQ 재조회 구간)에는 저장값이 부분 데이터 기준으로 남는다.
    dates가 비면(수집할 거래일이 없던 날) 기존처럼 최신 거래일만 계산한다.
    한 날짜가 실패해도 나머지는 계산하고, 끝에 실패 날짜를 모아 예외로 올린다.
    """
    if not dates:
        result = compute_market_breadth(market)
        return [result] if result else []

    results: list[dict] = []
    failed: list[date] = []
    for d in sorted(set(dates)):
        try:
            result = compute_market_breadth(market, d)
        except Exception:
            logger.exception("%s breadth %s 계산 실패 — 다음 날짜로 진행", market.upper(), d)
            failed.append(d)
            continue
        if result:
            results.append(result)

    if failed:
        raise RuntimeError(
            f"{market.upper()} breadth 재계산 실패 {len(failed)}일: {[d.isoformat() for d in failed]}"
        )
    return results


def recompute_market_breadth_since(market: str, start_date: date) -> list[dict]:
    """
    start_date 이후 price_daily에 있는 모든 거래일의 breadth를 다시 계산한다.

    NASDAQ 수집은 매 실행마다 start_date부터 다시 받아 늦게 도착한 행을 채우므로,
    수집이 실제로 쓴 start_date를 넘겨받아 같은 구간을 재계산한다(구간을 여기서
    따로 정하면 수집 구간이 바뀔 때 어긋난다).
    """
    with SyncSessionLocal() as session:
        dates = get_trading_days_since_sync(session, market, start_date)
    return recompute_market_breadth(market, dates)

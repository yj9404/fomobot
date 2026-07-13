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

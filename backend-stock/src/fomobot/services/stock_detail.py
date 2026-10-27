"""
종목 상세 — 기준일 종가, 기간별 등락률, 최대 5년 종가 시계열.

GET /api/stock/detail(JSON)과 토스 공유 카드(GET /api/og/toss/stock)가 이 모듈 하나를
공유한다. 두 곳이 같은 기준일에 대해 다른 숫자를 내지 않도록 계산은 여기서만 한다.

기간 구간은 랭킹 배치(compute_rankings)와 같은 방식이다:
  끝 = 기준일(시장 최신 거래일), 시작 = 끝 - N일(캘린더) 이하의 실제 거래일.
  등락률 = 구간 안 그 종목의 첫 종가 → 마지막 종가. 상장이 구간 시작보다 늦으면
  랭킹처럼 첫 거래일부터 계산하고, 실제 시작일(start_date)을 같이 내보낸다.

거래정지 종목:
  끝은 시장 최신 거래일로 고정하므로, 정지 이후 구간에는 종목 데이터가 없어
  등락률이 None이 된다. close_date(종목 자체 마지막 거래일)가 as_of보다 이르면
  프론트가 "마지막 거래일" 배지를 붙인다.

정정 중 종목(corporate_action_flag excluded/pending):
  close_adj 시계열이 오염되어 있으므로 수치를 하나도 내보내지 않고 status="correcting"만 준다.
  랭킹 배치·공유 카드와 같은 기준이다.

매수 시나리오·원금 환산은 하지 않는다 — 시세만 다룬다(백테스트 API와 분리된 이유).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.crud import (
    get_corporate_action_flag_status_async,
    get_last_trading_day_async,
    get_price_series_async,
    get_security_async,
)
from fomobot.services.calculator import PERIOD_TO_DAYS
from fomobot.services.share import BLOCKED_FLAG_STATUSES

DetailStatus = Literal["ok", "correcting", "no_data"]


class StockDetailError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class PeriodChange:
    change_pct: float
    start_date: date
    end_date: date


@dataclass(frozen=True)
class StockDetail:
    market: str
    ticker: str
    name: str
    is_active: bool
    status: DetailStatus
    as_of: date | None = None
    close: float | None = None
    close_date: date | None = None
    changes: dict[str, PeriodChange | None] = field(
        default_factory=lambda: {p: None for p in PERIOD_TO_DAYS}
    )
    series: list[tuple[date, float]] = field(default_factory=list)


def compute_change(rows: list[tuple[date, float]]) -> PeriodChange | None:
    """구간 안 첫 종가 → 마지막 종가. 2개 미만이거나 첫 종가가 0 이하면 None."""
    if len(rows) < 2:
        return None
    (start_date, start_price), (end_date, end_price) = rows[0], rows[-1]
    if not start_price or start_price <= 0:
        return None
    return PeriodChange(
        change_pct=(end_price / start_price - 1) * 100,
        start_date=start_date,
        end_date=end_date,
    )


async def build_stock_detail(
    session: AsyncSession,
    market: str,
    ticker: str,
    as_of: date | None = None,
) -> StockDetail:
    """
    as_of가 None이면 시장 최신 거래일 기준. 공유 카드는 as_of를 고정해 같은 URL이
    항상 같은 내용을 갖게 한다 — 이때 as_of는 시장 거래일이어야 한다(스냅하지 않음).
    """
    ticker = ticker.upper()
    security = await get_security_async(session, market, ticker)
    if security is None:
        raise StockDetailError(404, "존재하지 않는 종목입니다.")

    base = dict(
        market=market,
        ticker=ticker,
        name=security.name or ticker,
        is_active=bool(security.is_active),
    )

    flag_status = await get_corporate_action_flag_status_async(session, market, ticker)
    if flag_status in BLOCKED_FLAG_STATUSES:
        return StockDetail(**base, status="correcting")

    latest = await get_last_trading_day_async(session, market)
    if latest is None:
        return StockDetail(**base, status="no_data")

    if as_of is None:
        end = latest
    else:
        if as_of > latest:
            raise StockDetailError(400, "기준일이 최신 데이터일보다 늦습니다.")
        if await get_last_trading_day_async(session, market, as_of=as_of) != as_of:
            raise StockDetailError(404, "기준일이 거래일이 아닙니다.")
        end = as_of

    starts: dict[str, date] = {}
    for period, days in PERIOD_TO_DAYS.items():
        raw_start = end - timedelta(days=days)
        starts[period] = await get_last_trading_day_async(session, market, as_of=raw_start) or raw_start

    series = await get_price_series_async(session, market, ticker, min(starts.values()), end)
    if not series:
        return StockDetail(**base, status="no_data", as_of=end)

    changes = {
        period: compute_change([r for r in series if r[0] >= start])
        for period, start in starts.items()
    }
    return StockDetail(
        **base,
        status="ok",
        as_of=end,
        close=series[-1][1],
        close_date=series[-1][0],
        changes=changes,
        series=series,
    )

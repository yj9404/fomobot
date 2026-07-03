from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

DISCLAIMER = "투자 조언이 아닙니다. FomoBot은 지나간 걸 보여줄 뿐이에요."

PeriodLiteral = Literal["1d", "7d", "30d", "90d", "365d", "1825d"]
MarketLiteral = Literal["kospi", "nasdaq"]
CapTierLiteral = Literal["all", "small", "mid", "large"]
OrderLiteral = Literal["desc", "asc"]


class RankingItem(BaseModel):
    rank: int
    ticker: str
    name: str | None = None
    return_pct: float = Field(description="기간 수익률 (%)")
    mdd_pct: float | None = Field(None, description="최대낙폭 MDD (%, ≤ 0)")
    volatility_annualized_pct: float | None = Field(None, description="연율화 변동성 (%)")
    excess_return_vs_index_pct: float | None = Field(None, description="지수 대비 초과수익률 (%)")


class RankingsResponse(BaseModel):
    disclaimer: str = DISCLAIMER
    market: MarketLiteral
    period: PeriodLiteral
    as_of: date
    top: int
    cap_tier: CapTierLiteral = "all"
    order: OrderLiteral = "desc"
    rankings: list[RankingItem]

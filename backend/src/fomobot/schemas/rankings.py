from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

DISCLAIMER = "이 데이터는 투자 조언이 아닙니다. 참고 및 교육 목적으로만 사용하세요."

PeriodLiteral = Literal["1d", "7d", "30d", "90d", "365d", "1825d"]
MarketLiteral = Literal["kospi", "nasdaq"]


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
    rankings: list[RankingItem]

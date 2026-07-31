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
    has_news: bool | None = Field(
        None,
        description=(
            "관련 뉴스 캐시 존재 여부. KOSPI 단기 구간(1d/7d/30d)에서만 채워지며 "
            "그 외(NASDAQ, 90d 이상)는 null — 프론트는 null이면 인디케이터를 표시하지 않습니다."
        ),
    )
    halt_resumption: bool = Field(
        False,
        description=(
            "장기 거래정지 후 재개 첫 실거래일 여부. true면 재개일은 가격제한폭이 "
            "적용되지 않아 1d 등락이 커도 정상 — 프론트는 tooltip으로 설명해야 하며, "
            "값 자체를 의심하거나 제외해서는 안 됩니다. 현재는 1d period에서만 채워지고 "
            "다른 period는 항상 false입니다."
        ),
    )


class RankingsResponse(BaseModel):
    disclaimer: str = DISCLAIMER
    market: MarketLiteral
    period: PeriodLiteral
    as_of: date
    top: int
    cap_tier: CapTierLiteral = "all"
    order: OrderLiteral = "desc"
    rankings: list[RankingItem]

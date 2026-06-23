from datetime import date

from pydantic import BaseModel, Field

from fomobot.schemas.rankings import DISCLAIMER, MarketLiteral, PeriodLiteral


class BacktestItem(BaseModel):
    rank_at_as_of: int = Field(description="기준 시점 당시 랭킹 순위")
    ticker: str
    name: str | None = None
    return_pct_at_as_of: float = Field(description="기준 시점 당시 기간 수익률 (%)")
    current_return_pct: float | None = Field(
        None, description="기준 시점 매수 가정 시 현재까지 수익률 (%)"
    )


class BacktestResponse(BaseModel):
    disclaimer: str = DISCLAIMER
    survival_bias_warning: str = (
        "상장폐지 종목은 price_daily 테이블에서 누락되어 포함되지 않습니다. "
        "생존 편향(survivorship bias)으로 인해 실제 수익률보다 과대 계상될 수 있습니다."
    )
    market: MarketLiteral
    period: PeriodLiteral
    as_of: date
    top: int
    avg_current_return_pct: float | None = Field(
        None, description="포트폴리오 평균 현재 수익률 (동일 가중)"
    )
    items: list[BacktestItem]

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from fomobot.schemas.rankings import MarketLiteral


class ShareResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    market: MarketLiteral
    ticker: str
    name: str
    from_date: date = Field(alias="from", description="구간 시작 거래일 (이 날 종가에 매수)")
    to_date: date = Field(alias="to", description="구간 끝 거래일 (이 날 종가 기준 평가)")
    start_price: float = Field(description="from 종가 (close_adj)")
    end_price: float = Field(description="to 종가 (close_adj)")
    return_pct: float = Field(description="buy-and-hold 수익률 (%)")
    mdd_pct: float = Field(description="구간 내 최대낙폭 (%, ≤ 0)")
    principal: int = Field(description="원금 (KOSPI ₩1,000,000 / NASDAQ $10,000)")
    end_value: int = Field(description="to 시점 평가액 (principal과 같은 통화)")
    currency: str = Field(description="KRW | USD")

from datetime import date

from pydantic import BaseModel, Field

from fomobot.schemas.rankings import MarketLiteral


class BreadthResponse(BaseModel):
    market: MarketLiteral
    date: date
    advancers: int = Field(description="상승 종목 수")
    decliners: int = Field(description="하락 종목 수")
    unchanged: int = Field(description="보합 종목 수")
    excluded: int = Field(description="전일 종가 없어 등락 판정에서 제외된 종목 수(신규상장 등)")
    halted: int = Field(description="거래량 0 종목 수 (참고용, advancers/decliners/unchanged와 배타적이지 않음)")
    total: int = Field(description="advancers + decliners + unchanged + excluded")

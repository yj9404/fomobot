from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from fomobot.schemas.rankings import MarketLiteral, PeriodLiteral


class PeriodChange(BaseModel):
    change_pct: float = Field(description="기간 등락률 (%)")
    start_date: date = Field(
        description="실제 계산 시작 거래일. 상장이 기간 시작보다 늦으면 기간 시작일보다 뒤다."
    )
    end_date: date = Field(description="실제 계산 끝 거래일. 거래정지 중이면 as_of보다 이르다.")


class StockDetailResponse(BaseModel):
    market: MarketLiteral
    ticker: str
    name: str
    is_active: bool
    status: Literal["ok", "correcting", "no_data"] = Field(
        description="ok | correcting(데이터 정정 중 — 수치 없음) | no_data(시세 없음)"
    )
    as_of: date | None = Field(None, description="계산 기준일 (시장 최신 거래일)")
    close: float | None = Field(None, description="종목 마지막 거래일 종가 (close_adj)")
    close_date: date | None = Field(
        None, description="종목 마지막 거래일. as_of보다 이르면 거래정지 등으로 최근 시세가 없다."
    )
    changes: dict[PeriodLiteral, PeriodChange | None] = Field(
        description="기간별 등락률. 구간 안 데이터가 2개 미만이면 null."
    )
    series: list[tuple[date, float]] = Field(
        description="[날짜, 종가] 일별 시계열 (오름차순, 최대 5년)"
    )

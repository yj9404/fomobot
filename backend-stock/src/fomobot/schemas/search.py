from datetime import date

from pydantic import BaseModel, Field


class SecurityItem(BaseModel):
    ticker: str
    name: str | None = None
    is_active: bool


class SearchResponse(BaseModel):
    market: str
    query: str
    results: list[SecurityItem]


class DataCoverage(BaseModel):
    actual_start: date | None = None
    actual_end: date | None = None
    available_from: date | None = None
    trading_days: int
    warning: str | None = None


class QuoteResponse(BaseModel):
    ticker: str
    market: str
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    start_price: float | None = None
    end_price: float | None = None
    return_pct: float | None = Field(None, description="기간 수익률 (%)")
    mdd_pct: float | None = Field(None, description="최대낙폭 MDD (%, ≤ 0)")
    volatility_annualized_pct: float | None = Field(None, description="연율화 변동성 (%)")
    data_coverage: DataCoverage


class DateBoundsResponse(BaseModel):
    market: str
    min_date: date | None = None

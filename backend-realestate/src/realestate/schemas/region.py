from pydantic import BaseModel


class MonthlyDataPoint(BaseModel):
    deal_ym: str
    median_price_per_sqm: float | None  # 만원/㎡, None = 해당 월 거래 없음
    transaction_count: int


class RegionMeta(BaseModel):
    disclaimer: str
    recent_note: str
    data_range: str                     # "200601 ~ 202605" 형식


class RegionDetailResponse(BaseModel):
    sigungu_code: str
    sigungu_name: str
    eupmyeondong: str | None
    display_name: str
    level: str                          # 'gu' | 'dong'
    monthly_data: list[MonthlyDataPoint]
    meta: RegionMeta

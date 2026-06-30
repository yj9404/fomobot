from typing import Literal

from pydantic import BaseModel

from realestate.schemas.rankings import PeriodLiteral  # noqa: F401 — re-export

# 기존 DataStatusLiteral에 no_snapshot 추가
# no_snapshot: ReComplexStat에 단지는 있으나 해당 period 스냅샷 레코드가 없는 경우
SearchDataStatusLiteral = Literal["ok", "insufficient", "no_start", "no_end", "no_snapshot"]


class RegionItem(BaseModel):
    sido_code: str          # sigungu_code 앞 2자리 (11/28/41)
    sido_name: str          # 서울/인천/경기
    sigungu_code: str       # 5자리 코드 (rankings gu 필터에 그대로 사용)
    sigungu_name: str
    eupmyeondong: str


class RegionSearchResponse(BaseModel):
    query: str
    results: list[RegionItem]


class SearchResultItem(BaseModel):
    complex_key: str
    apt_name: str
    display_name: str | None        # 스냅샷 있으면 "서울 강남구 개포동 래미안개포1단지", 없으면 None
    sigungu_code: str
    sigungu_name: str | None        # no_snapshot이면 None일 수 있음
    eupmyeondong: str
    rank: int | None
    change_pct: float | None
    start_price: float | None       # 만원/㎡
    end_price: float | None         # 만원/㎡
    start_deal_amount: int | None   # 만원, 중위 거래금액
    end_deal_amount: int | None     # 만원
    start_tx_count: int | None
    end_tx_count: int | None
    start_ym: str | None
    end_ym: str | None
    data_status: SearchDataStatusLiteral
    insufficient_reason: str | None


class SearchResponse(BaseModel):
    query: str
    period: str
    snapshot_ym: str | None         # None = 해당 period 스냅샷 미존재
    results: list[SearchResultItem]


class ComplexMonthlyPoint(BaseModel):
    deal_ym: str
    median_price_per_sqm: float | None  # 만원/㎡
    transaction_count: int


class ComplexDetailResponse(BaseModel):
    complex_key: str
    apt_name: str
    display_name: str | None
    sigungu_code: str
    sigungu_name: str | None
    eupmyeondong: str
    monthly_data: list[ComplexMonthlyPoint]
    data_range: str | None          # "200601 ~ 202605"

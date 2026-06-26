from typing import Literal

from pydantic import BaseModel

PeriodLiteral = Literal["3m", "6m", "1y", "3y", "5y", "10y", "20y"]
DataStatusLiteral = Literal["ok", "insufficient", "no_start", "no_end"]

DISCLAIMER = (
    "이 서비스는 재미·교육 목적이며 투자 조언이 아닙니다. "
    "과거 상승률이 미래 수익을 보장하지 않습니다. "
    "FomoBot은 지나간 걸 보여줄 뿐이에요."
)

_WINDOW_OVERLAP_NOTE = (
    "3개월 구간은 시작·종료 윈도우가 1개월 겹쳐 상승률이 다소 과소평가될 수 있습니다."
)


class ComplexRankingItem(BaseModel):
    rank: int | None
    complex_key: str
    apt_name: str
    display_name: str
    sigungu_code: str
    sigungu_name: str
    eupmyeondong: str
    start_ym: str
    end_ym: str
    start_price: float | None       # 만원/㎡
    end_price: float | None         # 만원/㎡
    change_pct: float | None        # % (None = 계산 불가)
    start_tx_count: int | None
    end_tx_count: int | None
    data_status: DataStatusLiteral
    insufficient_reason: str | None


class ComplexRankingsMeta(BaseModel):
    snapshot_ym: str
    period: str
    total_complexes: int            # 랭킹 포함(ok) 단지 수
    is_recent_incomplete: bool
    windows_overlap: bool           # 3m 구간에서 창 겹침 여부
    window_note: str | None         # windows_overlap=True일 때 안내 문구
    recent_note: str
    disclaimer: str


class ComplexRankingsResponse(BaseModel):
    meta: ComplexRankingsMeta
    rankings: list[ComplexRankingItem]      # data_status='ok', rank 순
    excluded: list[ComplexRankingItem]      # 데이터 부족 등 제외 단지

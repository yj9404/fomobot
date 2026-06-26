from typing import Literal

from pydantic import BaseModel

PeriodLiteral = Literal["3m", "6m", "1y", "3y", "5y", "10y", "20y"]
LevelLiteral = Literal["gu", "dong"]
DataStatusLiteral = Literal["ok", "insufficient", "no_start", "no_end"]

DISCLAIMER = (
    "이 서비스는 재미·교육 목적이며 투자 조언이 아닙니다. "
    "과거 상승률이 미래 수익을 보장하지 않습니다. "
    "FomoBot은 지나간 걸 보여줄 뿐이에요."
)


class RankingItem(BaseModel):
    rank: int | None
    display_name: str
    sigungu_code: str
    sigungu_name: str
    eupmyeondong: str | None
    start_ym: str
    end_ym: str
    start_price: float | None       # 만원/㎡
    end_price: float | None         # 만원/㎡
    change_pct: float | None        # % (None = 계산 불가)
    start_tx_count: int | None
    end_tx_count: int | None
    data_status: DataStatusLiteral
    insufficient_reason: str | None


class RankingsMeta(BaseModel):
    snapshot_ym: str
    period: str
    level: str
    is_recent_incomplete: bool
    recent_note: str
    disclaimer: str


class RankingsResponse(BaseModel):
    meta: RankingsMeta
    rankings: list[RankingItem]     # data_status='ok', rank 순
    excluded: list[RankingItem]     # data_status!='ok' (데이터 부족 등)

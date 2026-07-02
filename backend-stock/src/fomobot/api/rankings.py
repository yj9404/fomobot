from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.crud import get_latest_snapshot_date, get_rankings
from fomobot.db.session import get_async_session
from fomobot.schemas.rankings import (
    CapTierLiteral,
    MarketLiteral,
    PeriodLiteral,
    RankingItem,
    RankingsResponse,
)

router = APIRouter(prefix="/api/stock", tags=["Rankings"])

# ── 시총 구간 임계값 ─────────────────────────────────────────────────────────
# KOSPI: 원화(KRW) 기준
_KOSPI_CAP = {
    "small": (None,          500_000_000_000),    # < 5,000억 원
    "mid":   (500_000_000_000, 5_000_000_000_000), # 5,000억 ~ 5조
    "large": (5_000_000_000_000, None),            # > 5조 원
}
# NASDAQ: USD 기준
_NASDAQ_CAP = {
    "small": (None,           2_000_000_000),      # < $2B
    "mid":   (2_000_000_000,  10_000_000_000),     # $2B ~ $10B
    "large": (10_000_000_000, None),               # > $10B
}

def _resolve_cap_bounds(
    market: str, cap_tier: CapTierLiteral
) -> tuple[int | None, int | None]:
    """cap_tier 문자열을 마켓별 (min, max) 원화/달러 절대값으로 변환."""
    if cap_tier == "all":
        return None, None
    table = _KOSPI_CAP if market == "kospi" else _NASDAQ_CAP
    return table[cap_tier]


@router.get(
    "/rankings",
    response_model=RankingsResponse,
    summary="기간별 상승률 랭킹 조회",
    description=(
        "저장된 랭킹 스냅샷을 반환합니다. "
        "데이터는 장 마감 후 배치에서 계산되며, 실시간 계산은 수행하지 않습니다."
    ),
)
async def get_rankings_endpoint(
    market: MarketLiteral = Query(..., description="마켓 (kospi | nasdaq)"),
    period: PeriodLiteral = Query(..., description="기간 (1d|7d|30d|90d|365d|1825d)"),
    top: int = Query(20, ge=1, le=300, description="상위 N개 (기본 20, 최대 300)"),
    as_of: date | None = Query(None, description="기준일 (YYYY-MM-DD). 생략 시 최신"),
    cap_tier: CapTierLiteral = Query("all", description="시총 구간 (all|small|mid|large)"),
    session: AsyncSession = Depends(get_async_session),
):
    snapshot_date = as_of
    if snapshot_date is None:
        snapshot_date = await get_latest_snapshot_date(session, market, period)

    if snapshot_date is None:
        raise HTTPException(
            status_code=404,
            detail=f"{market.upper()} {period} 랭킹 데이터가 없습니다. 배치가 아직 실행되지 않았을 수 있습니다.",
        )

    min_cap, max_cap = _resolve_cap_bounds(market, cap_tier)
    rows = await get_rankings(session, market, period, top, snapshot_date, min_cap, max_cap)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"{snapshot_date} 기준 {market.upper()} {period} {cap_tier} 랭킹 데이터가 없습니다.",
        )

    items = [
        RankingItem(
            rank=r.rank,
            ticker=r.ticker,
            name=r.name,
            return_pct=r.return_pct,
            mdd_pct=r.mdd_pct,
            volatility_annualized_pct=r.volatility_annualized_pct,
            excess_return_vs_index_pct=r.excess_return_pct,
        )
        for r in rows
    ]

    return RankingsResponse(
        market=market,
        period=period,
        as_of=snapshot_date,
        top=top,
        cap_tier=cap_tier,
        rankings=items,
    )

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.crud import get_latest_snapshot_date, get_rankings
from fomobot.db.session import get_async_session
from fomobot.schemas.rankings import (
    MarketLiteral,
    PeriodLiteral,
    RankingItem,
    RankingsResponse,
)

router = APIRouter(prefix="/api/stock", tags=["Rankings"])


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
    top: int = Query(20, ge=1, le=100, description="상위 N개 (기본 20, 최대 100)"),
    as_of: date | None = Query(None, description="기준일 (YYYY-MM-DD). 생략 시 최신"),
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

    rows = await get_rankings(session, market, period, top, snapshot_date)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"{snapshot_date} 기준 {market.upper()} {period} 랭킹 데이터가 없습니다.",
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
        rankings=items,
    )

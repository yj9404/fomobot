from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.crud import get_latest_market_breadth_async
from fomobot.db.session import get_async_session
from fomobot.schemas.breadth import BreadthResponse
from fomobot.schemas.rankings import MarketLiteral

router = APIRouter(prefix="/api", tags=["Breadth"])


@router.get(
    "/breadth",
    response_model=BreadthResponse,
    summary="시장 breadth(상승/하락/보합 종목 수) 최신 스냅샷",
    description=(
        "market_breadth_daily에 저장된 최신 1행을 반환합니다(실시간 계산 없음). "
        "배치가 아직 실행되지 않았거나 백필 전이라 데이터가 없으면 404를 반환합니다."
    ),
)
async def get_breadth_endpoint(
    market: MarketLiteral = Query(..., description="마켓 (kospi | nasdaq)"),
    session: AsyncSession = Depends(get_async_session),
):
    row = await get_latest_market_breadth_async(session, market)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"{market.upper()} breadth 데이터가 없습니다.",
        )
    return BreadthResponse(
        market=row.market,
        date=row.date,
        advancers=row.advancers,
        decliners=row.decliners,
        unchanged=row.unchanged,
        excluded=row.excluded,
        halted=row.halted,
        total=row.total,
    )

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.config import settings
from fomobot.db.crud import get_latest_snapshot_date, get_rankings
from fomobot.db.session import get_async_session
from fomobot.schemas.rankings import (
    CapTierLiteral,
    MarketLiteral,
    OrderLiteral,
    PeriodLiteral,
    RankingItem,
    RankingsResponse,
)

router = APIRouter(prefix="/api/stock", tags=["Rankings"])


def _resolve_cap_bounds(
    market: str, cap_tier: CapTierLiteral
) -> tuple[int | None, int | None]:
    """cap_tier → (min_cap, max_cap). 경계값은 config.py 단일 소스에서 읽는다.
    소형: cap < mid_lo  /  중형: mid_lo ≤ cap < large_lo  /  대형: cap ≥ large_lo
    """
    if cap_tier == "all":
        return None, None
    if market == "kospi":
        mid_lo, large_lo = settings.kospi_cap_mid_lo, settings.kospi_cap_large_lo
    else:
        mid_lo, large_lo = settings.nasdaq_cap_mid_lo, settings.nasdaq_cap_large_lo
    return {
        "small": (None,    mid_lo),
        "mid":   (mid_lo,  large_lo),
        "large": (large_lo, None),
    }[cap_tier]


@router.get(
    "/rankings",
    response_model=RankingsResponse,
    summary="기간별 상승/하락률 랭킹 조회",
    description=(
        "저장된 랭킹 스냅샷을 반환합니다. "
        "order=desc(기본)는 상승률 상위, order=asc는 하락률 상위입니다. "
        "데이터는 장 마감 후 배치에서 계산되며, 실시간 계산은 수행하지 않습니다."
    ),
)
async def get_rankings_endpoint(
    market: MarketLiteral = Query(..., description="마켓 (kospi | nasdaq)"),
    period: PeriodLiteral = Query(..., description="기간 (1d|7d|30d|90d|365d|1825d)"),
    top: int = Query(20, ge=1, le=300, description="상위 N개 (기본 20, 최대 300)"),
    as_of: date | None = Query(None, description="기준일 (YYYY-MM-DD). 생략 시 최신"),
    cap_tier: CapTierLiteral = Query("all", description="시총 구간 (all|small|mid|large)"),
    order: OrderLiteral = Query("desc", description="정렬 방향 (desc=상승률 상위, asc=하락률 상위)"),
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
    rows = await get_rankings(session, market, period, top, snapshot_date, min_cap, max_cap, order)

    # cap_tier 필터 적용 후 결과가 없으면 빈 목록 반환 (에러가 아닌 빈 상태)
    # cap_tier="all"인데 비면 배치 오류이므로 404 유지
    if not rows and cap_tier != "all":
        return RankingsResponse(
            market=market,
            period=period,
            as_of=snapshot_date,
            top=top,
            cap_tier=cap_tier,
            order=order,
            rankings=[],
        )

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
        cap_tier=cap_tier,
        order=order,
        rankings=items,
    )

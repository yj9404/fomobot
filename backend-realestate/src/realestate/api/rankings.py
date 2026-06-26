from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from realestate.db.crud import get_latest_snapshot_ym, get_rankings_async
from realestate.db.session import get_async_session
from realestate.schemas.rankings import (
    DISCLAIMER,
    LevelLiteral,
    PeriodLiteral,
    RankingItem,
    RankingsMeta,
    RankingsResponse,
)

router = APIRouter(prefix="/api/realestate", tags=["Real Estate Rankings"])

# 최근 2개월 이내 end_ym이면 신고 진행 중 가능성 있음
_RECENT_NOTE = "최근 1~2개월 거래는 신고 진행 중일 수 있어 수치가 바뀔 수 있습니다."


def _is_recent_incomplete(snapshot_ym: str) -> bool:
    today = date.today()
    current_ym = f"{today.year}{today.month:02d}"
    prev_ym_date = date(today.year, today.month, 1)
    if prev_ym_date.month == 1:
        prev = f"{prev_ym_date.year - 1}12"
    else:
        prev = f"{prev_ym_date.year}{prev_ym_date.month - 1:02d}"
    return snapshot_ym >= prev


@router.get(
    "/rankings",
    response_model=RankingsResponse,
    summary="아파트 평단가 상승률 랭킹",
    description=(
        "수도권 시군구(구/동) 단위 아파트 ㎡당 단가 중위값 기반 상승률 랭킹. "
        "데이터는 월별 배치에서 계산되며 실시간 계산은 수행하지 않습니다. "
        "거래 건수가 최소 기준에 미달하는 지역은 excluded 목록에 포함됩니다."
    ),
)
async def get_rankings_endpoint(
    level: LevelLiteral = Query("gu", description="집계 단위 (gu=구, dong=동)"),
    period: PeriodLiteral = Query(..., description="기간 (3m|6m|1y|3y|5y|10y|20y)"),
    region: str | None = Query(None, description="시도 필터 (11=서울, 28=인천, 41=경기)"),
    top: int = Query(20, ge=1, le=100, description="상위 N개 (기본 20)"),
    session: AsyncSession = Depends(get_async_session),
):
    snapshot_ym = await get_latest_snapshot_ym(session, level, period)
    if snapshot_ym is None:
        raise HTTPException(
            status_code=404,
            detail=f"{level} {period} 랭킹 데이터가 없습니다. 배치가 아직 실행되지 않았을 수 있습니다.",
        )

    rows = await get_rankings_async(session, level, period, snapshot_ym, top, region)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"{snapshot_ym} 기준 {level}/{period} 랭킹 데이터가 없습니다.",
        )

    ok_items: list[RankingItem] = []
    excluded_items: list[RankingItem] = []
    ok_count = 0

    for row in rows:
        item = RankingItem(
            rank=row.rank,
            display_name=row.display_name,
            sigungu_code=row.sigungu_code,
            sigungu_name=row.sigungu_name,
            eupmyeondong=row.eupmyeondong,
            start_ym=row.start_ym,
            end_ym=row.end_ym,
            start_price=float(row.start_price) if row.start_price is not None else None,
            end_price=float(row.end_price) if row.end_price is not None else None,
            change_pct=float(row.change_pct) if row.change_pct is not None else None,
            start_tx_count=row.start_tx_count,
            end_tx_count=row.end_tx_count,
            data_status=row.data_status,
            insufficient_reason=row.insufficient_reason,
        )
        if row.data_status == "ok":
            if ok_count < top:
                ok_items.append(item)
                ok_count += 1
        else:
            excluded_items.append(item)

    meta = RankingsMeta(
        snapshot_ym=snapshot_ym,
        period=period,
        level=level,
        is_recent_incomplete=_is_recent_incomplete(snapshot_ym),
        recent_note=_RECENT_NOTE,
        disclaimer=DISCLAIMER,
    )
    return RankingsResponse(meta=meta, rankings=ok_items, excluded=excluded_items)

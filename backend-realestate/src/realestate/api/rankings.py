from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from realestate.db.crud import get_complex_rankings_async, get_latest_complex_snapshot_ym
from realestate.db.session import get_async_session
from realestate.schemas.rankings import (
    DISCLAIMER,
    ComplexRankingItem,
    ComplexRankingsMeta,
    ComplexRankingsResponse,
    PeriodLiteral,
    SegmentItem,
    SegmentsResponse,
    _WINDOW_OVERLAP_NOTE,
)
from realestate.segments import SEGMENTS

router = APIRouter(prefix="/api/realestate", tags=["Real Estate Rankings"])

_RECENT_NOTE = "최근 1~2개월 거래는 신고 진행 중일 수 있어 수치가 바뀔 수 있습니다."


def _is_recent_incomplete(snapshot_ym: str) -> bool:
    today = date.today()
    month = today.month - 1
    year = today.year
    if month <= 0:
        month += 12
        year -= 1
    prev_ym = f"{year}{month:02d}"
    return snapshot_ym >= prev_ym


@router.get(
    "/segments",
    response_model=SegmentsResponse,
    summary="학군 세그먼트 목록",
    description="단지 랭킹 필터로 사용할 수 있는 학군 세그먼트 목록을 반환합니다.",
)
async def get_segments_endpoint():
    items = [
        SegmentItem(seg_key=key, label=meta["label"], description=meta["description"])
        for key, meta in SEGMENTS.items()
    ]
    return SegmentsResponse(segments=items)


@router.get(
    "/rankings",
    response_model=ComplexRankingsResponse,
    summary="아파트 단지 평단가 상승률 랭킹",
    description=(
        "수도권 아파트 단지 단위 ㎡당 단가 중위값 기반 상승률 랭킹. "
        "sido/gu/dong/seg는 랭킹 단위가 아닌 범위 필터입니다. "
        "seg가 지정되면 sido/gu/dong은 무시됩니다. "
        "데이터는 월별 배치에서 계산되며 실시간 계산은 수행하지 않습니다."
    ),
)
async def get_rankings_endpoint(
    period: PeriodLiteral = Query(..., description="기간 (3m|6m|1y|3y|5y|10y|20y)"),
    sido: str | None = Query(None, description="시도 필터 (11=서울, 28=인천, 41=경기)"),
    gu: str | None = Query(None, description="구 필터 — 5자리 시군구 코드 (예: 11680=강남구)"),
    dong: str | None = Query(None, description="동 필터 — 법정동명 (예: 개포동)"),
    seg: str | None = Query(None, description="학군 세그먼트 키 (예: 목동, 대치). seg 지정 시 sido/gu/dong 무시."),
    top: int = Query(20, ge=1, le=100, description="상위 N개 (기본 20)"),
    session: AsyncSession = Depends(get_async_session),
):
    seg_dongs: list[tuple[str, str]] | None = None
    if seg is not None:
        seg_def = SEGMENTS.get(seg)
        if seg_def is None:
            raise HTTPException(
                status_code=400,
                detail=f"알 수 없는 seg 값: '{seg}'. /api/realestate/segments 에서 유효한 목록을 확인하세요.",
            )
        seg_dongs = seg_def["dongs"]

    snapshot_ym = await get_latest_complex_snapshot_ym(session, period)
    if snapshot_ym is None:
        raise HTTPException(
            status_code=404,
            detail=f"{period} 랭킹 데이터가 없습니다. 배치가 아직 실행되지 않았을 수 있습니다.",
        )

    rows = await get_complex_rankings_async(
        session, period, snapshot_ym, top,
        sido=sido, gu=gu, dong=dong, seg=seg_dongs,
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"{snapshot_ym} 기준 {period} 랭킹 데이터가 없습니다.",
        )

    ok_items: list[ComplexRankingItem] = []
    excluded_items: list[ComplexRankingItem] = []
    ok_count = 0
    windows_overlap = False

    for row in rows:
        if row.windows_overlap:
            windows_overlap = True

        item = ComplexRankingItem(
            rank=row.rank,
            complex_key=row.complex_key,
            apt_name=row.apt_name,
            display_name=row.display_name,
            sigungu_code=row.sigungu_code,
            sigungu_name=row.sigungu_name,
            eupmyeondong=row.eupmyeondong,
            start_ym=row.start_ym,
            end_ym=row.end_ym,
            start_price=float(row.start_price) if row.start_price is not None else None,
            end_price=float(row.end_price) if row.end_price is not None else None,
            start_deal_amount=int(row.start_deal_amount) if row.start_deal_amount is not None else None,
            end_deal_amount=int(row.end_deal_amount) if row.end_deal_amount is not None else None,
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

    meta = ComplexRankingsMeta(
        snapshot_ym=snapshot_ym,
        period=period,
        total_complexes=ok_count,
        is_recent_incomplete=_is_recent_incomplete(snapshot_ym),
        windows_overlap=windows_overlap,
        window_note=_WINDOW_OVERLAP_NOTE if windows_overlap else None,
        recent_note=_RECENT_NOTE,
        disclaimer=DISCLAIMER,
    )
    return ComplexRankingsResponse(meta=meta, rankings=ok_items, excluded=excluded_items)

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from realestate.batch.normalize import normalize_apt_name
from realestate.db.crud import (
    get_complex_meta_async,
    get_complex_monthly_async,
    get_latest_complex_snapshot_ym,
    get_sigungu_name_map_async,
    search_complexes_async,
    search_regions_async,
)
from realestate.db.session import get_async_session
from realestate.schemas.rankings import PeriodLiteral
from realestate.schemas.search import (
    ComplexDetailResponse,
    ComplexMonthlyPoint,
    RegionItem,
    RegionSearchResponse,
    SearchResponse,
    SearchResultItem,
)

router = APIRouter(prefix="/api/realestate", tags=["Real Estate Search"])

_SIDO_NAMES = {"11": "서울", "28": "인천", "41": "경기"}


@router.get(
    "/regions",
    response_model=RegionSearchResponse,
    summary="지역(구/동) 이름 검색",
    description=(
        "시군구명 또는 법정동명 부분일치로 지역 목록을 반환한다. "
        "결과의 sigungu_code를 /rankings?gu= 필터에 그대로 사용할 수 있다."
    ),
)
async def search_regions_endpoint(
    q: str = Query(..., min_length=1, max_length=50, description="시군구명 또는 법정동명 (부분일치)"),
    session: AsyncSession = Depends(get_async_session),
):
    rows = await search_regions_async(session, q)
    results = [
        RegionItem(
            sido_code=r.sigungu_code[:2],
            sido_name=_SIDO_NAMES.get(r.sigungu_code[:2], ""),
            sigungu_code=r.sigungu_code,
            sigungu_name=r.sigungu_name,
            eupmyeondong=r.eupmyeondong,
        )
        for r in rows
    ]
    return RegionSearchResponse(query=q, results=results)


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="아파트명 검색 (기간 스냅샷 포함)",
    description=(
        "아파트명 부분일치로 단지를 검색하고, 해당 period의 최신 스냅샷 지표를 반환한다. "
        "data_status='no_snapshot': 단지는 존재하지만 해당 period 스냅샷 레코드 없음. "
        "data_status='insufficient'|'no_start'|'no_end': 스냅샷은 있으나 거래 데이터 부족. "
        "results가 빈 리스트: 검색어와 일치하는 단지 자체가 없음."
    ),
)
async def search_complexes_endpoint(
    q: str = Query(..., min_length=1, max_length=100, description="아파트명 (부분일치, 띄어쓰기 무시)"),
    period: PeriodLiteral = Query(..., description="기간 (3m|6m|1y|3y|5y|10y|20y)"),
    sido: str | None = Query(None, description="시도 필터 — 앞 2자리 코드 (11=서울, 28=인천, 41=경기)"),
    gu: str | None = Query(None, description="구 필터 — 5자리 시군구 코드"),
    dong: str | None = Query(None, description="동 필터 — 법정동명 부분일치"),
    session: AsyncSession = Depends(get_async_session),
):
    q_norm = normalize_apt_name(q)

    snapshot_ym = await get_latest_complex_snapshot_ym(session, period)
    if snapshot_ym is None:
        return SearchResponse(query=q, period=period, snapshot_ym=None, results=[])

    stat_rows, snap_rows = await search_complexes_async(
        session, q_norm, period, snapshot_ym,
        sido=sido, gu=gu, dong=dong,
    )

    if not stat_rows:
        return SearchResponse(query=q, period=period, snapshot_ym=snapshot_ym, results=[])

    snap_by_key = {s.complex_key: s for s in snap_rows}

    # no_snapshot 단지에 대해 sigungu_name 별도 조회
    no_snap_codes = [
        r.sigungu_code for r in stat_rows if r.complex_key not in snap_by_key
    ]
    sigungu_map = await get_sigungu_name_map_async(session, list(set(no_snap_codes)))

    results: list[SearchResultItem] = []
    for stat in stat_rows:
        snap = snap_by_key.get(stat.complex_key)
        if snap:
            item = SearchResultItem(
                complex_key=stat.complex_key,
                apt_name=snap.apt_name,
                display_name=snap.display_name,
                sigungu_code=snap.sigungu_code,
                sigungu_name=snap.sigungu_name,
                eupmyeondong=snap.eupmyeondong,
                rank=snap.rank,
                change_pct=float(snap.change_pct) if snap.change_pct is not None else None,
                start_price=float(snap.start_price) if snap.start_price is not None else None,
                end_price=float(snap.end_price) if snap.end_price is not None else None,
                start_deal_amount=int(snap.start_deal_amount) if snap.start_deal_amount is not None else None,
                end_deal_amount=int(snap.end_deal_amount) if snap.end_deal_amount is not None else None,
                start_tx_count=snap.start_tx_count,
                end_tx_count=snap.end_tx_count,
                start_ym=snap.start_ym,
                end_ym=snap.end_ym,
                data_status=snap.data_status,
                insufficient_reason=snap.insufficient_reason,
            )
        else:
            item = SearchResultItem(
                complex_key=stat.complex_key,
                apt_name=stat.apt_name,
                display_name=None,
                sigungu_code=stat.sigungu_code,
                sigungu_name=sigungu_map.get(stat.sigungu_code),
                eupmyeondong=stat.eupmyeondong,
                rank=None,
                change_pct=None,
                start_price=None,
                end_price=None,
                start_deal_amount=None,
                end_deal_amount=None,
                start_tx_count=None,
                end_tx_count=None,
                start_ym=None,
                end_ym=None,
                data_status="no_snapshot",
                insufficient_reason=None,
            )
        results.append(item)

    return SearchResponse(query=q, period=period, snapshot_ym=snapshot_ym, results=results)


@router.get(
    "/complex/{complex_key}",
    response_model=ComplexDetailResponse,
    summary="단지 월별 평단가 시계열",
    description=(
        "특정 단지의 ㎡당 단가 중위값 월별 시계열을 반환한다. "
        "complex_key는 /search 응답의 complex_key 값을 그대로 사용한다."
    ),
)
async def get_complex_detail(
    complex_key: str,
    start_ym: str = Query("200601", description="조회 시작 년월 (YYYYMM)"),
    end_ym: str | None = Query(None, description="조회 종료 년월 (YYYYMM). 생략 시 이번 달"),
    session: AsyncSession = Depends(get_async_session),
):
    if len(complex_key) != 40 or not all(c in "0123456789abcdef" for c in complex_key):
        raise HTTPException(status_code=422, detail="complex_key는 40자리 hex 문자열이어야 합니다.")

    if end_ym is None:
        today = date.today()
        end_ym = f"{today.year}{today.month:02d}"

    meta = await get_complex_meta_async(session, complex_key)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"complex_key={complex_key} 단지가 없습니다.")

    monthly_rows = await get_complex_monthly_async(session, complex_key, start_ym, end_ym)

    monthly_data = [
        ComplexMonthlyPoint(
            deal_ym=r.deal_ym,
            median_price_per_sqm=float(r.median_price_per_sqm) if r.median_price_per_sqm else None,
            transaction_count=r.transaction_count,
        )
        for r in monthly_rows
    ]

    yms = [p.deal_ym for p in monthly_data]
    data_range = f"{yms[0]} ~ {yms[-1]}" if yms else None

    # meta 컬럼은 스냅샷 기준(5컬럼)이거나 stat 기준(3컬럼)
    has_snap_meta = hasattr(meta, "display_name")
    return ComplexDetailResponse(
        complex_key=complex_key,
        apt_name=meta.apt_name,
        display_name=meta.display_name if has_snap_meta else None,
        sigungu_code=meta.sigungu_code,
        sigungu_name=meta.sigungu_name if has_snap_meta else None,
        eupmyeondong=meta.eupmyeondong,
        monthly_data=monthly_data,
        data_range=data_range,
    )

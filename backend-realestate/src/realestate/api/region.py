from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from realestate.db.crud import get_region_monthly_stats_async
from realestate.db.session import get_async_session
from realestate.schemas.rankings import DISCLAIMER
from realestate.schemas.region import MonthlyDataPoint, RegionDetailResponse, RegionMeta

router = APIRouter(prefix="/api/realestate", tags=["Real Estate Region"])

_RECENT_NOTE = "최근 1~2개월 거래는 신고 진행 중일 수 있어 수치가 바뀔 수 있습니다."

_SIDO_NAMES = {"11": "서울", "28": "인천", "41": "경기"}


def _display_name(sigungu_code: str, sigungu_name: str, eupmyeondong: str | None) -> str:
    sido = _SIDO_NAMES.get(sigungu_code[:2], "")
    if eupmyeondong:
        return f"{sigungu_name} {eupmyeondong}"
    return f"{sido} {sigungu_name}".strip()


@router.get(
    "/region/{sigungu_code}",
    response_model=RegionDetailResponse,
    summary="특정 구/동 평단가 월별 추이",
    description=(
        "특정 시군구의 ㎡당 단가 중위값 월별 시계열을 반환합니다. "
        "eupmyeondong 파라미터를 지정하면 동 단위, 생략하면 구 단위로 집계된 데이터를 반환합니다."
    ),
)
async def get_region_detail(
    sigungu_code: str,
    eupmyeondong: str | None = Query(None, description="법정동명. 생략 시 구 단위 집계"),
    start_ym: str = Query("200601", description="조회 시작 년월 (YYYYMM)"),
    end_ym: str = Query(None, description="조회 종료 년월 (YYYYMM). 생략 시 최신"),
    session: AsyncSession = Depends(get_async_session),
):
    if len(sigungu_code) != 5 or not sigungu_code.isdigit():
        raise HTTPException(status_code=422, detail="sigungu_code는 5자리 숫자여야 합니다.")

    if end_ym is None:
        from datetime import date
        today = date.today()
        end_ym = f"{today.year}{today.month:02d}"

    rows = await get_region_monthly_stats_async(
        session, sigungu_code, eupmyeondong, start_ym, end_ym
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"sigungu_code={sigungu_code} 데이터가 없습니다. 수집이 아직 실행되지 않았을 수 있습니다.",
        )

    sigungu_name = sigungu_code  # re_monthly_stat에는 name이 없음 → 클라이언트가 별도 매핑하거나 rankings API에서 조합
    level = "dong" if eupmyeondong else "gu"

    monthly_data = [
        MonthlyDataPoint(
            deal_ym=r.deal_ym,
            median_price_per_sqm=float(r.median_price_per_sqm) if r.median_price_per_sqm else None,
            transaction_count=r.transaction_count,
        )
        for r in rows
    ]

    actual_yms = [p.deal_ym for p in monthly_data]
    data_range = f"{actual_yms[0]} ~ {actual_yms[-1]}" if actual_yms else ""

    display = _display_name(sigungu_code, sigungu_name, eupmyeondong)

    return RegionDetailResponse(
        sigungu_code=sigungu_code,
        sigungu_name=sigungu_name,
        eupmyeondong=eupmyeondong,
        display_name=display,
        level=level,
        monthly_data=monthly_data,
        meta=RegionMeta(
            disclaimer=DISCLAIMER,
            recent_note=_RECENT_NOTE,
            data_range=data_range,
        ),
    )

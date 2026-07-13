from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from realestate.config import settings
from realestate.db.crud import get_complex_meta_async, get_region_news_for_complex_async
from realestate.db.session import get_async_session
from realestate.schemas.news import ComplexNewsResponse, NewsArticle

router = APIRouter(prefix="/api/realestate", tags=["News"])


@router.get(
    "/news/{complex_key}",
    response_model=ComplexNewsResponse,
    summary="단지가 속한 동/구 관련 뉴스 (최대 3건)",
    description=(
        "배치가 미리 수집해 둔 뉴스 캐시를 반환합니다(실시간 검색 없음). "
        "단지 뉴스가 아니라 단지가 속한 동(우선)/구(동 결과 부족 시 폴백) 뉴스입니다. "
        "뉴스가 없으면 articles가 빈 배열입니다 — 억지 매칭을 하지 않습니다."
    ),
)
async def get_complex_news_endpoint(
    complex_key: str,
    session: AsyncSession = Depends(get_async_session),
):
    meta = await get_complex_meta_async(session, complex_key)
    if meta is None:
        return ComplexNewsResponse(complex_key=complex_key, articles=[])

    rows, region_label, granularity = await get_region_news_for_complex_async(
        session, meta.sigungu_code, meta.eupmyeondong, settings.region_news_ttl_days,
    )
    articles = [
        NewsArticle(title=r.title, link=r.link, published_at=r.published_at)
        for r in rows
    ]
    return ComplexNewsResponse(
        complex_key=complex_key,
        region_label=region_label,
        granularity=granularity,
        articles=articles,
    )

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from realestate.config import settings
from realestate.db.crud import get_complex_news_async
from realestate.db.session import get_async_session
from realestate.schemas.news import ComplexNewsResponse, NewsArticle

router = APIRouter(prefix="/api/realestate", tags=["News"])


@router.get(
    "/news/{complex_key}",
    response_model=ComplexNewsResponse,
    summary="단지 관련 뉴스 (최대 3건)",
    description=(
        "배치가 미리 수집해 둔 뉴스 캐시를 반환합니다(실시간 검색 없음). "
        "뉴스가 없으면 articles가 빈 배열입니다 — 억지 매칭을 하지 않습니다."
    ),
)
async def get_complex_news_endpoint(
    complex_key: str,
    session: AsyncSession = Depends(get_async_session),
):
    rows = await get_complex_news_async(session, complex_key, settings.complex_news_ttl_days)
    articles = [
        NewsArticle(title=r.title, link=r.link, published_at=r.published_at)
        for r in rows
    ]
    return ComplexNewsResponse(complex_key=complex_key, articles=articles)

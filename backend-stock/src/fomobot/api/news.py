from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.config import settings
from fomobot.db.crud import get_stock_news_async
from fomobot.db.session import get_async_session
from fomobot.schemas.news import NewsArticle, StockNewsResponse

router = APIRouter(prefix="/api/stock", tags=["News"])


@router.get(
    "/news/{ticker}",
    response_model=StockNewsResponse,
    summary="종목 관련 뉴스 (최대 3건)",
    description=(
        "배치가 미리 수집해 둔 뉴스 캐시를 반환합니다(실시간 검색 없음). "
        "뉴스가 없으면 articles가 빈 배열입니다 — 억지 매칭을 하지 않습니다."
    ),
)
async def get_stock_news_endpoint(
    ticker: str,
    session: AsyncSession = Depends(get_async_session),
):
    rows = await get_stock_news_async(session, ticker, settings.stock_news_ttl_days)
    articles = [
        NewsArticle(title=r.title, link=r.link, published_at=r.published_at)
        for r in rows
    ]
    return StockNewsResponse(ticker=ticker, articles=articles)

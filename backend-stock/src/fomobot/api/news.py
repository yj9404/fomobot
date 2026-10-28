from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.config import settings
from fomobot.db.crud import get_stock_news_async
from fomobot.db.session import get_async_session
from fomobot.schemas.news import NewsArticle, StockNewsResponse, TossNewsArticle, TossNewsResponse
from fomobot.services.news_display import is_advice_title, press_name, safe_web_host

router = APIRouter(prefix="/api/stock", tags=["News"])

# 배치는 종목당 5건까지 저장하지만 웹 화면은 기존대로 3건만 보여준다.
WEB_NEWS_LIMIT = 3
TOSS_NEWS_LIMIT = 5


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
        for r in rows[:WEB_NEWS_LIMIT]
    ]
    return StockNewsResponse(ticker=ticker, articles=articles)


@router.get(
    "/news/{ticker}/toss",
    response_model=TossNewsResponse,
    summary="토스판 종목 관련 뉴스 (최대 5건)",
    description=(
        "웹과 같은 뉴스 캐시에서 http/https가 아닌 링크와 권유·전망형 제목(매수·추천·목표가 등)을 "
        "빼고, 언론사 이름을 붙여 반환합니다. 뉴스가 없으면 articles가 빈 배열입니다."
    ),
)
async def get_toss_stock_news_endpoint(
    ticker: str,
    session: AsyncSession = Depends(get_async_session),
):
    rows = await get_stock_news_async(session, ticker, settings.stock_news_ttl_days)
    articles: list[TossNewsArticle] = []
    for r in rows:
        host = safe_web_host(r.link)
        if host is None or is_advice_title(r.title):
            continue
        articles.append(TossNewsArticle(
            title=r.title, source=press_name(host), url=r.link, published_at=r.published_at,
        ))
        if len(articles) == TOSS_NEWS_LIMIT:
            break
    return TossNewsResponse(ticker=ticker, articles=articles)

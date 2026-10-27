"""
종목 상세 엔드포인트 — 토스 미니앱 상세 화면용.

  GET /api/stock/detail?market=&ticker=

계산은 services/stock_detail.build_stock_detail 하나로 한다(토스 공유 카드와 공유).
데이터는 일 1회 배치로 바뀌므로 성공 응답은 짧게(5분) 캐시하고, 오류는 no-store.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.session import get_async_session
from fomobot.schemas.rankings import MarketLiteral
from fomobot.schemas.stock_detail import StockDetailResponse
from fomobot.services.stock_detail import StockDetailError, build_stock_detail

router = APIRouter(prefix="/api/stock", tags=["Stock Detail"])

DETAIL_CACHE = "public, max-age=300"


@router.get(
    "/detail",
    response_model=StockDetailResponse,
    summary="종목 상세 — 종가, 기간별 등락률, 최대 5년 종가 시계열",
)
async def stock_detail_endpoint(
    response: Response,
    market: MarketLiteral = Query(..., description="마켓 (kospi | nasdaq)"),
    ticker: str = Query(..., min_length=1, max_length=20, description="종목코드"),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        detail = await build_stock_detail(session, market, ticker)
    except StockDetailError as e:
        raise HTTPException(
            status_code=e.status_code, detail=e.detail, headers={"Cache-Control": "no-store"}
        )
    response.headers["Cache-Control"] = DETAIL_CACHE
    return StockDetailResponse(**asdict(detail))

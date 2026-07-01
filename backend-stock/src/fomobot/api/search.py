from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.crud import (
    get_global_price_min_date_async,
    get_price_history_bounds_async,
    get_price_series_async,
    get_security_name,
    search_securities,
)
from fomobot.db.session import AsyncSessionLocal
from fomobot.schemas.rankings import MarketLiteral, PeriodLiteral
from fomobot.schemas.search import DataCoverage, DateBoundsResponse, QuoteResponse, SearchResponse, SecurityItem
from fomobot.services.calculator import PERIOD_TO_DAYS, compute_quote_metrics

router = APIRouter(prefix="/api/stock", tags=["Search"])


async def _get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/date-bounds", response_model=DateBoundsResponse)
async def get_date_bounds(
    market: MarketLiteral,
    session: AsyncSession = Depends(_get_session),
):
    """시장 전체 주가 데이터의 가장 이른 날짜를 반환한다. 날짜 선택기의 min 범위 설정에 사용."""
    min_date = await get_global_price_min_date_async(session, market)
    return DateBoundsResponse(market=market, min_date=min_date)


@router.get("/search", response_model=SearchResponse)
async def search_stock(
    market: MarketLiteral,
    q: str = Query(..., min_length=1, max_length=100, description="종목코드 또는 종목명(부분일치)"),
    session: AsyncSession = Depends(_get_session),
):
    """
    종목코드 접두 매칭 또는 종목명 부분일치로 securities_master를 검색한다.
    결과는 정확 코드 매칭 → 코드 접두 매칭 → 이름 부분 매칭 순으로 정렬되며 최대 50건.
    """
    results = await search_securities(session, market, q)
    return SearchResponse(
        market=market,
        query=q,
        results=[
            SecurityItem(ticker=r.ticker, name=r.name, is_active=r.is_active)
            for r in results
        ],
    )


@router.get("/quote", response_model=QuoteResponse)
async def get_quote(
    market: MarketLiteral,
    ticker: str = Query(..., min_length=1, max_length=20, description="종목코드"),
    period: PeriodLiteral | None = Query(None, description="고정 기간 (1d/7d/30d/90d/365d/1825d)"),
    start: date | None = Query(None, description="시작일 (YYYY-MM-DD). period 미사용 시 필수."),
    end: date | None = Query(None, description="종료일 (YYYY-MM-DD). period 미사용 시 필수."),
    session: AsyncSession = Depends(_get_session),
):
    """
    단일 종목의 기간 수익률·MDD·변동성을 PriceDaily에서 직접 계산해 반환한다.

    - period 또는 start+end 중 하나를 지정.
    - 요청 기간이 보유 이력을 벗어나면 에러 대신 data_coverage.warning에 상황을 명시.
    - 보유 이력 기본값: init_history.py --years 6 실행 기준 최대 6년.
    """
    if period is None and (start is None or end is None):
        raise HTTPException(
            status_code=400,
            detail="period 또는 start+end 를 지정하세요.",
        )
    if period is not None and (start is not None or end is not None):
        raise HTTPException(
            status_code=400,
            detail="period 와 start/end 는 함께 사용할 수 없습니다.",
        )
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=400, detail="start 가 end 보다 늦을 수 없습니다.")

    ticker = ticker.upper()

    if period:
        end_date = date.today()
        start_date = end_date - timedelta(days=PERIOD_TO_DAYS[period])
    else:
        start_date, end_date = start, end  # type: ignore[assignment]

    avail_from, avail_to = await get_price_history_bounds_async(session, market, ticker)

    warning: str | None = None
    if avail_from is not None and start_date < avail_from:
        avail_years = round((date.today() - avail_from).days / 365, 1)
        warning = (
            f"데이터 보유 이력: 약 {avail_years}년 ({avail_from} ~ {avail_to}). "
            "요청 기간의 일부가 이력 범위를 벗어납니다."
        )

    price_rows = await get_price_series_async(session, market, ticker, start_date, end_date)
    name = await get_security_name(session, market, ticker)

    if not price_rows:
        return QuoteResponse(
            ticker=ticker,
            market=market,
            name=name,
            data_coverage=DataCoverage(
                available_from=avail_from,
                trading_days=0,
                warning=warning or "해당 기간에 데이터가 없습니다.",
            ),
        )

    prices = pd.Series(
        [p for _, p in price_rows],
        index=pd.DatetimeIndex([d for d, _ in price_rows]),
    )
    metrics = compute_quote_metrics(prices)
    actual_start = price_rows[0][0]
    actual_end = price_rows[-1][0]

    return QuoteResponse(
        ticker=ticker,
        market=market,
        name=name,
        start_date=actual_start,
        end_date=actual_end,
        start_price=price_rows[0][1],
        end_price=price_rows[-1][1],
        return_pct=metrics["return_pct"],
        mdd_pct=metrics["mdd_pct"],
        volatility_annualized_pct=metrics["volatility_annualized_pct"],
        data_coverage=DataCoverage(
            actual_start=actual_start,
            actual_end=actual_end,
            available_from=avail_from,
            trading_days=len(price_rows),
            warning=warning,
        ),
    )

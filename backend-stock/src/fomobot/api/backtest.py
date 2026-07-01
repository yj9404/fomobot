"""
백테스트 엔드포인트.

"N일 전 top 종목을 그때 매수했다면 현재 수익률은?"을 계산한다.

수익률 계산 방식 (재작성 후):
  - as_of 시점 주가: ranking_snapshot.close_price_at_snapshot (저장된 값)
  - 현재 주가: price_daily 최신 날짜의 종가 (최근 N일만 유지해도 동작)
  - price_daily 과거분(as_of 이전)은 더 이상 필요하지 않다.

생존 편향 주의:
  상장폐지 종목은 price_daily 최신 날짜에 행이 없으므로 결과에 포함되지 않는다.
  이로 인해 실제 수익률 대비 과대 계상될 수 있다 (survivorship bias).
  응답의 survival_bias_warning 필드에 이를 명시한다.

  주의 — 폴백(fallback) 금지:
    오늘 주가가 없을 때 as_of 주가로 대체하면 수익률이 0으로 왜곡된다.
    오늘 주가가 없는 경우 current_return_pct = None 을 반환한다.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.crud import (
    get_latest_prices_async,
    get_latest_snapshot_date,
    get_nearest_snapshot_date,
    get_rankings,
)
from fomobot.db.session import get_async_session
from fomobot.schemas.backtest import BacktestItem, BacktestResponse
from fomobot.schemas.rankings import MarketLiteral, PeriodLiteral

router = APIRouter(prefix="/api/stock", tags=["Backtest"])


@router.get(
    "/backtest",
    response_model=BacktestResponse,
    summary="백테스트 — 과거 top 종목의 현재 수익률",
    description=(
        "as_of 시점의 top N 종목을 그때 매수했다고 가정하고 "
        "현재(오늘)까지의 수익률을 계산합니다. "
        "상장폐지 종목은 포함되지 않아 생존 편향이 존재합니다."
    ),
)
async def backtest_endpoint(
    market: MarketLiteral = Query(..., description="마켓 (kospi | nasdaq)"),
    as_of: date = Query(..., description="기준 시점 (YYYY-MM-DD)"),
    period: PeriodLiteral = Query(..., description="기준 시점 기준 랭킹 산출 기간"),
    top: int = Query(20, ge=1, le=100, description="상위 N개 (기본 20, 최대 100)"),
    session: AsyncSession = Depends(get_async_session),
):
    # 1) as_of 이하의 가장 가까운 스냅샷 날짜 조회 (주간 백필 등 정확한 날짜가 없을 때 대응)
    actual_date = await get_nearest_snapshot_date(session, market, period, as_of)
    if actual_date is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{as_of} 이전 {market.upper()} {period} 랭킹 스냅샷이 없습니다. "
                f"백필 배치가 실행되지 않았거나 데이터가 부족합니다."
            ),
        )

    snapshot_rows = await get_rankings(session, market, period, top, actual_date)
    if not snapshot_rows:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{actual_date} {market.upper()} {period} 랭킹 스냅샷이 비어 있습니다."
            ),
        )

    # 2) 기준일과 최신 날짜가 같으면 오늘 가격 미수집 상태 — 모두 None
    latest_date = await get_latest_snapshot_date(session, market, "1d")
    if latest_date is not None and actual_date >= latest_date:
        current_returns: dict[str, float | None] = {}
    else:
        current_returns = await _compute_current_returns(session, market, snapshot_rows)

    items = []
    for row in snapshot_rows:
        cur_ret = current_returns.get(row.ticker)
        items.append(
            BacktestItem(
                rank_at_as_of=row.rank,
                ticker=row.ticker,
                name=row.name,
                return_pct_at_as_of=row.return_pct,
                current_return_pct=cur_ret,
            )
        )

    valid_returns = [i.current_return_pct for i in items if i.current_return_pct is not None]
    avg_return = sum(valid_returns) / len(valid_returns) if valid_returns else None

    return BacktestResponse(
        market=market,
        period=period,
        as_of=as_of,
        actual_as_of=actual_date,
        top=top,
        avg_current_return_pct=avg_return,
        items=items,
    )


async def _compute_current_returns(
    session: AsyncSession,
    market: str,
    snapshot_rows,
) -> dict[str, float | None]:
    """
    as_of 시점 저장 주가 → 최신 주가 수익률 계산.

    - as_of 주가: ranking_snapshot.close_price_at_snapshot (price_daily 과거분 불필요)
    - 오늘 주가: price_daily 최신 날짜 단 1일 조회

    생존 편향:
      상장폐지 종목은 오늘 price_daily에 행이 없으므로 자연스럽게 None 처리.
      close_price_at_snapshot이 NULL(backfill 미완료 등)인 경우도 None.
      어떠한 폴백도 하지 않는다.
    """
    if not snapshot_rows:
        return {}

    tickers = [r.ticker for r in snapshot_rows]

    # 오늘(최신) 주가 조회 — price_daily 최근 N일만 있어도 동작
    today_prices: dict[str, float | None] = await get_latest_prices_async(
        session, market, tickers
    )

    returns: dict[str, float | None] = {}
    for row in snapshot_rows:
        price_start = row.close_price_at_snapshot  # 저장된 as_of 종가
        price_end = today_prices.get(row.ticker)    # 오늘 종가 (없으면 None)

        if price_start and price_end and price_start > 0:
            returns[row.ticker] = (price_end / price_start - 1) * 100
        else:
            # price_start가 None: backfill 미완료 또는 수집 실패
            # price_end가 None: 상장폐지 (생존 편향 의도된 동작)
            returns[row.ticker] = None

    return returns

"""
백테스트 엔드포인트.

"N일 전 top 종목을 그때 매수했다면 현재 수익률은?"을 계산한다.

생존 편향 주의:
  상장폐지 종목은 price_daily 테이블에서 누락되므로 결과에 포함되지 않는다.
  이로 인해 실제 수익률 대비 과대 계상될 수 있다 (survivorship bias).
  응답의 survival_bias_warning 필드에 이를 명시한다.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.crud import get_latest_snapshot_date, get_rankings
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
    # 1) as_of 시점의 랭킹 스냅샷 조회
    snapshot_rows = await get_rankings(session, market, period, top, as_of)

    if not snapshot_rows:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{as_of} 기준 {market.upper()} {period} 랭킹 스냅샷이 없습니다. "
                f"해당 날짜 배치가 실행되지 않았거나 데이터가 부족합니다."
            ),
        )

    # 2) 오늘 날짜 최신 스냅샷 조회 (현재 가격 대용)
    latest_date = await get_latest_snapshot_date(session, market, "1d")
    today_rows_map: dict[str, float] = {}

    if latest_date:
        today_rows = await get_rankings(session, market, "1825d", 500, latest_date)
        # 종목별 현재 가격은 ranking_snapshot에 직접 없으므로
        # price_daily를 조회하는 것이 정확하나, 여기서는 현재 수익률을
        # 기준일 종가 기준으로 재계산하기 위해 별도 price 조회가 필요하다.
        # 간소화: as_of 랭킹의 return_pct와 오늘 랭킹의 return_pct 차이는
        # 의미가 없으므로, price_daily를 직접 조회해 수익률을 계산한다.
        # → 실제 구현은 아래 _compute_current_returns()에서 수행.
        pass

    current_returns = await _compute_current_returns(
        session, market, snapshot_rows, latest_date
    )

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
        top=top,
        avg_current_return_pct=avg_return,
        items=items,
    )


async def _compute_current_returns(
    session: AsyncSession,
    market: str,
    snapshot_rows,
    latest_date: date | None,
) -> dict[str, float | None]:
    """
    기준일(as_of) 당시 가격 → 최신 가격 수익률 계산.

    price_daily 테이블을 직접 조회해 as_of 날짜와 latest_date 가격을 비교한다.
    상장폐지 종목은 latest_date 데이터가 없으므로 자연스럽게 None 처리된다.

    생존 편향:
      상장폐지 종목 누락으로 인해 포트폴리오 평균 수익률이 실제보다
      높게 산출될 수 있다 (survivorship bias).
    """
    if not snapshot_rows or latest_date is None:
        return {}

    tickers = [r.ticker for r in snapshot_rows]
    as_of_date = snapshot_rows[0].snapshot_date if hasattr(snapshot_rows[0], "snapshot_date") else None

    if as_of_date is None:
        return {}

    # 동기 세션은 배치에서 사용하고, 여기서는 async 세션 사용
    # raw SQL로 두 날짜의 가격을 한 번에 조회
    from sqlalchemy import text

    placeholders = ", ".join(f":t{i}" for i in range(len(tickers)))
    params = {f"t{i}": t for i, t in enumerate(tickers)}
    params["market"] = market
    params["as_of"] = as_of_date
    params["latest"] = latest_date

    query = text(f"""
        SELECT ticker,
               MAX(CASE WHEN date = :as_of   THEN close_adj END) AS price_start,
               MAX(CASE WHEN date = :latest   THEN close_adj END) AS price_end
        FROM price_daily
        WHERE market = :market
          AND ticker IN ({placeholders})
          AND date IN (:as_of, :latest)
        GROUP BY ticker
    """)

    result = await session.execute(query, params)
    rows = result.fetchall()

    returns: dict[str, float | None] = {}
    for row in rows:
        if row.price_start and row.price_end and row.price_start > 0:
            returns[row.ticker] = (row.price_end / row.price_start - 1) * 100
        else:
            returns[row.ticker] = None

    return returns

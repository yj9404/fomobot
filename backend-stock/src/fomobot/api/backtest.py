"""
백테스트 엔드포인트.

시나리오별("그때 샀다면") 수익률·MDD를 계산한다.
- buy-and-hold: 시작일 전량 매수 후 보유 (1단계, 검증 완료).
- DCA: 기간별 분할 매수 (2단계, 검증 완료). 1d/7d는 분할이 성립하지 않아 항상 None.

가격은 price_daily.close_adj를 종목별로 직접 조회한다(get_price_series_async) —
랭킹 스냅샷의 top-N 소속 여부와 무관하게 해당 티커 하나의 시계열만 가져온다.
buy-and-hold와 DCA는 이 시계열을 한 번만 조회해 공유한다(추가 DB 조회 없음).

구간 시작일은 compute_rankings 배치와 동일한 방식으로 결정한다:
"actual_date - period일"을 캘린더 일수로 계산한 뒤, 그 날짜 이하 중 실제
거래일(get_last_trading_day_async)로 스냅한다.

끝가는 시장 전체 최신일(MAX(date))이 아니라, 그 종목 자체의 구간 내
가장 최근 종가를 쓴다 — 특정 종목의 수집 지연이 다른 종목에 영향을 주지 않는다.

생존 편향 주의:
  상장폐지 등으로 구간 내 가격이 2개 미만이면 buy_and_hold=None.
  as_of 주가로 대체하는 폴백은 하지 않는다.

DCA 결손 구간 주의:
  상장일이 구간 시작일보다 늦으면 앞쪽 일부 회차는 매수할 가격이 없다.
  회차 수를 조용히 줄이지 않고, executed_installments/total_installments와
  warning에 실제 집행된 회차 수를 명시한다.

목록/상세 분리:
  GET /backtest        — top N 목록. equity curve 없음(payload 절약).
  GET /backtest/detail  — 단일 종목. equity curve 포함(/api/stock/quote와 동일한
                          "단일 종목 상세" 패턴).
  두 엔드포인트 모두 아래 _ScenarioCompute(계산 결과 + 원본 equity curve)를
  공유하고, 각자 다른 pydantic 모델로 직렬화할 뿐 계산 수식은 동일하다.
"""

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.crud import (
    get_last_trading_day_async,
    get_nearest_snapshot_date,
    get_price_series_async,
    get_rankings,
    get_security_name,
)
from fomobot.db.session import get_async_session
from fomobot.schemas.backtest import (
    BacktestDetailResponse,
    BacktestDetailScenarios,
    BacktestItem,
    BacktestResponse,
    BacktestScenarios,
    EquityPoint,
    ScenarioDetail,
    ScenarioResult,
)
from fomobot.schemas.rankings import MarketLiteral, PeriodLiteral
from fomobot.services.calculator import PERIOD_TO_DAYS, compute_mdd

router = APIRouter(prefix="/api/stock", tags=["Backtest"])

DETAIL_PRINCIPAL = 1_000_000.0


@dataclass
class _ScenarioCompute:
    """계산 결과 + 원본(비정규화) equity curve. 목록/상세 두 엔드포인트가 공유하는
    내부 표현이며, pydantic 응답 모델이 아니다 — 각 엔드포인트가 필요한 형태로만
    변환해서 내보낸다 (equity_curve는 상세 응답에만 노출)."""

    final_return_pct: float
    mdd_pct: float | None
    warning: str | None
    executed_installments: int | None
    total_installments: int | None
    equity_curve: list[tuple[date, float]]  # buy_and_hold: close_adj 원가. dca: 원금=1.0 비율.


@router.get(
    "/backtest",
    response_model=BacktestResponse,
    summary="백테스트 — 과거 top 종목의 시나리오별 수익률",
    description=(
        "as_of 시점의 top N 종목을 그때 매수했다고 가정하고 "
        "시나리오별(buy-and-hold / DCA) 수익률과 실측 MDD를 계산합니다. "
        "상장폐지 종목은 포함되지 않아 생존 편향이 존재합니다. "
        "equity curve는 포함하지 않습니다 — 단일 종목 상세는 /backtest/detail을 쓰세요."
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

    # 2) 시나리오 계산 — 종목별 price_daily 직접 조회 (top-N 소속 여부 무관)
    start_date = await _resolve_start_date(session, market, period, actual_date)

    items = []
    valid_returns: list[float] = []
    for row in snapshot_rows:
        price_rows = await get_price_series_async(
            session, market, row.ticker, start_date, actual_date
        )
        bh = _compute_buy_and_hold(price_rows)
        dca = _compute_dca(price_rows, period, start_date, actual_date)

        if bh is not None:
            valid_returns.append(bh.final_return_pct)

        items.append(
            BacktestItem(
                rank_at_as_of=row.rank,
                ticker=row.ticker,
                name=row.name,
                return_pct_at_as_of=row.return_pct,
                scenarios=BacktestScenarios(
                    buy_and_hold=_to_scenario_result(bh),
                    dca=_to_scenario_result(dca),
                ),
            )
        )

    avg_return = sum(valid_returns) / len(valid_returns) if valid_returns else None

    return BacktestResponse(
        market=market,
        period=period,
        as_of=as_of,
        actual_as_of=actual_date,
        top=top,
        avg_buy_and_hold_return_pct=avg_return,
        items=items,
    )


@router.get(
    "/backtest/detail",
    response_model=BacktestDetailResponse,
    summary="백테스트 상세 — 단일 종목의 equity curve 포함 시나리오",
    description=(
        "단일 종목에 대해 buy-and-hold/DCA 시나리오의 일별 평가액(equity curve)을 "
        "포함한 상세 결과를 반환합니다. top N 목록 조회는 /backtest를 쓰세요."
    ),
)
async def backtest_detail_endpoint(
    market: MarketLiteral = Query(..., description="마켓 (kospi | nasdaq)"),
    ticker: str = Query(..., min_length=1, max_length=20, description="종목코드"),
    as_of: date = Query(..., description="기준 시점 (YYYY-MM-DD)"),
    period: PeriodLiteral = Query(..., description="기준 시점 기준 랭킹 산출 기간"),
    session: AsyncSession = Depends(get_async_session),
):
    ticker = ticker.upper()

    actual_date = await get_nearest_snapshot_date(session, market, period, as_of)
    if actual_date is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{as_of} 이전 {market.upper()} {period} 랭킹 스냅샷이 없습니다. "
                f"백필 배치가 실행되지 않았거나 데이터가 부족합니다."
            ),
        )

    start_date = await _resolve_start_date(session, market, period, actual_date)
    price_rows = await get_price_series_async(session, market, ticker, start_date, actual_date)
    name = await get_security_name(session, market, ticker)

    bh = _compute_buy_and_hold(price_rows)
    dca = _compute_dca(price_rows, period, start_date, actual_date)

    return BacktestDetailResponse(
        market=market,
        ticker=ticker,
        name=name,
        period=period,
        as_of=as_of,
        actual_as_of=actual_date,
        principal=DETAIL_PRINCIPAL,
        first_traded_date=price_rows[0][0] if price_rows else None,
        scenarios=BacktestDetailScenarios(
            buy_and_hold=_to_scenario_detail_buy_and_hold(bh, DETAIL_PRINCIPAL),
            dca=_to_scenario_detail_dca(dca, DETAIL_PRINCIPAL),
        ),
    )


async def _resolve_start_date(
    session: AsyncSession,
    market: str,
    period: str,
    actual_date: date,
) -> date:
    """
    구간 시작일 = actual_date - period일(캘린더) → 실제 거래일로 스냅.
    compute_rankings.py의 start_date 스냅 로직과 동일한 함수를 재사용한다.
    """
    days = PERIOD_TO_DAYS[period]
    raw_start = actual_date - timedelta(days=days)
    return await get_last_trading_day_async(session, market, as_of=raw_start) or raw_start


def _to_scenario_result(c: "_ScenarioCompute | None") -> ScenarioResult | None:
    """목록 응답용 — equity_curve를 뺀 스칼라만."""
    if c is None:
        return None
    return ScenarioResult(
        final_return_pct=c.final_return_pct,
        mdd_pct=c.mdd_pct,
        warning=c.warning,
        executed_installments=c.executed_installments,
        total_installments=c.total_installments,
    )


def _to_scenario_detail_buy_and_hold(
    c: "_ScenarioCompute | None", principal: float
) -> ScenarioDetail | None:
    """
    buy-and-hold equity_curve(원본: close_adj 원가) → 시작가 기준 정규화 후 원금 스케일.
    value = price / price[0] * principal. 스칼라(final_return_pct/mdd_pct)는 건드리지 않는다.
    """
    if c is None:
        return None
    start_price = c.equity_curve[0][1]
    curve = [
        EquityPoint(date=d, value=(v / start_price) * principal)
        for d, v in c.equity_curve
    ]
    return ScenarioDetail(
        final_return_pct=c.final_return_pct,
        mdd_pct=c.mdd_pct,
        warning=c.warning,
        executed_installments=c.executed_installments,
        total_installments=c.total_installments,
        equity_curve=curve,
    )


def _to_scenario_detail_dca(
    c: "_ScenarioCompute | None", principal: float
) -> ScenarioDetail | None:
    """
    dca equity_curve(원본: 원금=1.0 비율) → 원금 스케일만 곱하면 됨.
    value = ratio * principal. 스칼라는 건드리지 않는다.
    """
    if c is None:
        return None
    curve = [EquityPoint(date=d, value=v * principal) for d, v in c.equity_curve]
    return ScenarioDetail(
        final_return_pct=c.final_return_pct,
        mdd_pct=c.mdd_pct,
        warning=c.warning,
        executed_installments=c.executed_installments,
        total_installments=c.total_installments,
        equity_curve=curve,
    )


def _compute_buy_and_hold(
    price_rows: list[tuple[date, float]],
) -> _ScenarioCompute | None:
    """
    buy-and-hold 시나리오: 구간 시작일 종가에 원금 전량 매수, actual_date까지 보유.

    - 시작가/끝가: 종목별 시계열의 첫 행/마지막 행 (market 전체 최신일 아님)
    - MDD: 그 구간의 실제 가격 경로에서 compute_mdd로 계산 (휴리스틱 아님)
    - 이 함수의 계산식은 검증 완료 상태이므로 수정하지 않는다.
    """
    if len(price_rows) < 2:
        # 데이터 부족(상장폐지·신규상장 등) — 폴백 없이 None
        return None

    start_price = price_rows[0][1]
    end_price = price_rows[-1][1]

    if not start_price or start_price <= 0:
        return None

    final_return_pct = (end_price / start_price - 1) * 100

    prices = pd.Series(
        [p for _, p in price_rows],
        index=pd.DatetimeIndex([d for d, _ in price_rows]),
    )
    mdd_series = compute_mdd(prices.to_frame("_ticker"))
    mdd_pct = float(mdd_series.iloc[0]) if not mdd_series.empty else None

    return _ScenarioCompute(
        final_return_pct=final_return_pct,
        mdd_pct=mdd_pct,
        warning=None,
        executed_installments=None,
        total_installments=None,
        equity_curve=list(price_rows),
    )


# 기간별 DCA 분할 횟수. 1d/7d는 분할이 성립하지 않아 DCA 없음(None 유지).
# 30d=주간 4회, 90d=월간 3회, 365d=월간 12회, 1825d=분기 20회.
DCA_INSTALLMENTS: dict[str, int | None] = {
    "1d": None,
    "7d": None,
    "30d": 4,
    "90d": 3,
    "365d": 12,
    "1825d": 20,
}


def _compute_dca(
    price_rows: list[tuple[date, float]],
    period: str,
    start_date: date,
    actual_date: date,
) -> _ScenarioCompute | None:
    """
    DCA(분할 매수) 시나리오: 구간을 N등분한 시점마다 원금/N씩 매수해 actual_date까지 보유.

    - price_rows: buy-and-hold와 동일하게 이미 조회된 [start_date, actual_date] 시계열을
      그대로 재사용한다 (추가 DB 조회 없음).
    - start_date/actual_date: buy-and-hold와 동일한, "명목상" 구간 경계(호출부에서
      get_last_trading_day_async로 스냅한 값)를 그대로 받는다. price_rows[0]/[-1]로
      되짚어 window을 다시 잡으면 안 된다 — 상장일이 늦어 price_rows[0]이 이미
      뒤로 밀린 종목(NVCT 등)에서는 그렇게 하면 명목 구간 자체가 조용히 짧아져
      "회차 부족" 경고가 사라지는 버그가 생긴다(실측으로 확인됨).
    - 분할 시점 = start_date + i*(명목 구간일수/N) 이후 첫 거래일로 스냅.
      N=1이면 분할 시점이 start_date 하나뿐이라 buy-and-hold와 수학적으로 동일해진다
      (원금 전량을 시작일에 한 번 매수하는 것과 같은 식이 되므로).
    - equity curve = 그날까지 산 주식 수 × 그날 종가 + 아직 투입 안 한 원금 비율(현금, 0% 취급).
      이 커브에 compute_mdd를 적용하면 매수 분산 효과가 반영된 실측 MDD가 나온다.
    - 분할 시점이 종목의 실제 첫 거래일(price_rows[0])보다 앞서면(상장 전) 그 회차는
      매수 자체가 불가능하므로 건너뛰고, 실제 집행 회차 수를 warning/executed_installments에
      남긴다 (조용히 회차를 줄이지 않음).
    - 이 함수의 계산식은 검증 완료 상태이므로 수정하지 않는다(equity_curve를 반환값에
      담아 버리지 않게 된 것 외에는 이전과 동일).
    """
    n = DCA_INSTALLMENTS.get(period)
    if n is None or len(price_rows) < 2:
        return None

    dates = [d for d, _ in price_rows]
    prices = [p for _, p in price_rows]
    window_days = (actual_date - start_date).days

    # 분할 시점(목표일) → 그 날짜 이후 첫 거래일의 인덱스.
    # 목표일이 종목의 실제 첫 거래일보다 앞서면(상장 전이라 데이터 자체가 없으면)
    # 해당 회차는 매수 불가로 스킵한다.
    install_idx: list[int] = []
    for i in range(n):
        target = start_date + timedelta(days=round(i * window_days / n))
        if target < dates[0]:
            continue
        idx = next((j for j, d in enumerate(dates) if d >= target), None)
        if idx is not None:
            install_idx.append(idx)

    executed = len(install_idx)
    if executed == 0:
        return None

    unit = 1.0 / n  # 원금 비율 단위 (금액이 아니라 %만 필요하므로 원금=1.0 기준)
    cum_shares = 0.0
    invested = 0.0
    equity: list[float] = []
    pi = 0
    for i, price in enumerate(prices):
        while pi < len(install_idx) and install_idx[pi] == i:
            if price and price > 0:
                cum_shares += unit / price
                invested += unit
            pi += 1
        equity.append(cum_shares * price + (1.0 - invested))

    final_return_pct = (equity[-1] - 1.0) * 100

    eq_series = pd.Series(equity, index=pd.DatetimeIndex(dates))
    mdd_series = compute_mdd(eq_series.to_frame("_dca"))
    mdd_pct = float(mdd_series.iloc[0]) if not mdd_series.empty else None

    warning = None
    if executed < n:
        warning = (
            f"{executed}/{n}회만 집행됨 "
            "(상장일·데이터 시작일이 구간 시작일보다 늦어 일부 회차 매수 불가)"
        )

    return _ScenarioCompute(
        final_return_pct=final_return_pct,
        mdd_pct=mdd_pct,
        warning=warning,
        executed_installments=executed,
        total_installments=n,
        equity_curve=list(zip(dates, equity)),
    )

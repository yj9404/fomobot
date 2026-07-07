from datetime import date

from pydantic import BaseModel, Field

from fomobot.schemas.rankings import DISCLAIMER, MarketLiteral, PeriodLiteral


class ScenarioResult(BaseModel):
    final_return_pct: float = Field(description="최종 수익률 (%)")
    mdd_pct: float | None = Field(None, description="구간 내 실측 최대낙폭 MDD (%, ≤ 0)")
    warning: str | None = Field(
        None, description="데이터 결손 등으로 일부만 계산/집행됐을 때의 경고 (예: DCA 일부 회차 미집행)"
    )
    executed_installments: int | None = Field(
        None, description="DCA 실제 집행 회차 수 (buy_and_hold거나 DCA 미해당 기간이면 None)"
    )
    total_installments: int | None = Field(
        None, description="DCA 총 회차 수 (buy_and_hold거나 DCA 미해당 기간이면 None)"
    )


class EquityPoint(BaseModel):
    date: date
    value: float = Field(description="원금(principal) 기준 평가액. 단위=원.")


class ScenarioDetail(ScenarioResult):
    equity_curve: list[EquityPoint] = Field(
        description="일별 평가액 시계열 (원금 기준, 원 단위로 정규화됨). 목록 API(/backtest)에는 포함되지 않는다."
    )


class BacktestScenarios(BaseModel):
    buy_and_hold: ScenarioResult | None = Field(
        None, description="시작일 전량 매수 후 보유 시나리오 (데이터 부족·상장폐지 시 None)"
    )
    dca: ScenarioResult | None = Field(
        None,
        description=(
            "분할 매수(DCA) 시나리오. 1d/7d 기간은 분할이 성립하지 않아 항상 None. "
            "상장일이 구간 시작일보다 늦어 일부 회차를 집행 못하면 warning/executed_installments에 "
            "명시하고 가능한 회차만으로 계산한다."
        ),
    )


class BacktestDetailScenarios(BaseModel):
    buy_and_hold: ScenarioDetail | None = None
    dca: ScenarioDetail | None = None


class BacktestItem(BaseModel):
    rank_at_as_of: int = Field(description="기준 시점 당시 랭킹 순위")
    ticker: str
    name: str | None = None
    return_pct_at_as_of: float = Field(description="기준 시점 당시 기간 수익률 (%)")
    scenarios: BacktestScenarios


class BacktestResponse(BaseModel):
    disclaimer: str = DISCLAIMER
    survival_bias_warning: str = (
        "상장폐지 종목은 최신 주가가 없어 포함되지 않습니다. "
        "생존 편향(survivorship bias)으로 인해 실제 수익률보다 과대 계상될 수 있습니다."
    )
    market: MarketLiteral
    period: PeriodLiteral
    as_of: date
    actual_as_of: date = Field(description="실제 사용된 스냅샷 날짜 (as_of 이하 가장 가까운 날짜)")
    top: int
    avg_buy_and_hold_return_pct: float | None = Field(
        None, description="포트폴리오 평균 buy-and-hold 수익률 (동일 가중)"
    )
    items: list[BacktestItem]


class BacktestDetailResponse(BaseModel):
    """단일 종목 상세 — equity curve 포함. 목록(top N) 조회는 BacktestResponse를 쓴다."""

    disclaimer: str = DISCLAIMER
    survival_bias_warning: str = (
        "상장폐지 종목은 최신 주가가 없어 포함되지 않습니다. "
        "생존 편향(survivorship bias)으로 인해 실제 수익률보다 과대 계상될 수 있습니다."
    )
    market: MarketLiteral
    ticker: str
    name: str | None = None
    period: PeriodLiteral
    as_of: date
    actual_as_of: date = Field(description="실제 사용된 스냅샷 날짜 (as_of 이하 가장 가까운 날짜)")
    principal: float = Field(1_000_000.0, description="원금 (원 단위, 표시용 고정값)")
    first_traded_date: date | None = Field(
        None,
        description=(
            "조회 구간 내 이 종목의 첫 거래일(price_rows[0]의 날짜). "
            "주의: 상장일이 아니라 '조회 구간 내' 첫 거래일이다. 상장이 늦어 "
            "구간 시작일보다 데이터가 늦게 시작하는 종목(DCA executed_installments < "
            "total_installments)에서만 실제 상장일과 일치한다. 결손이 없는 종목에서는 "
            "그냥 구간 시작일 근처 거래일일 뿐이므로 이 필드를 상장일로 오인해 쓰면 안 된다."
        ),
    )
    scenarios: BacktestDetailScenarios

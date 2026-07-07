"""
백테스트 시나리오 엔진(_compute_dca) 단위 테스트.

이전 버전은 이미 폐기된 close_price_at_snapshot 기반 로직을 실제 코드와
분리된 채로 복제한 순수 함수를 테스트하고 있어, 실제 구현이 바뀌어도
계속 통과하는 거짓 안전감을 줬다 (교체 이력: current_return_pct 방식 →
scenarios.buy_and_hold/dca 방식). 이번 버전은 실제 프로덕션 함수
`fomobot.api.backtest._compute_dca`를 직접 import해서 검증한다.

`_compute_dca`는 DB에 접근하지 않는 순수 함수(price_rows를 인자로 받음)라
async/DB mock 없이 단위 테스트가 가능하다.

핵심 검증:
  1. N=1 항등 — 분할 횟수 1은 원금 전액을 시작일에 한 번 매수하는 것과
     같으므로, buy-and-hold와 수학적으로 동일해야 한다.
  2. 정상 DCA — 여러 회차로 나뉘어 실행되고, buy-and-hold와 다른 값이 나온다.
  3. 결손 구간 — 상장일(시계열 시작)이 명목 구간 시작일보다 늦으면 일부
     회차를 건너뛰고, "M/N회만 집행됨" 경고를 남긴다. 조용히 회차 수를
     줄이지 않는다.
  4. 1d/7d는 DCA가 성립하지 않아 항상 None.
"""

from datetime import date, timedelta

import pytest

from fomobot.api.backtest import _compute_dca, DCA_INSTALLMENTS
from fomobot.services.calculator import compute_mdd
import pandas as pd


def make_series(prices: list[float], start: date) -> list[tuple[date, float]]:
    """평일만 순서대로 이어붙인 (date, price) 시계열 생성 (주말 스킵 없이 단순 연속일)."""
    return [(start + timedelta(days=i), p) for i, p in enumerate(prices)]


def buy_and_hold_return(price_rows: list[tuple[date, float]]) -> float:
    """buy-and-hold 공식(참고용 재계산 — _compute_scenarios와 동일한 수식)."""
    return (price_rows[-1][1] / price_rows[0][1] - 1) * 100


def buy_and_hold_mdd(price_rows: list[tuple[date, float]]) -> float:
    prices = pd.Series(
        [p for _, p in price_rows],
        index=pd.DatetimeIndex([d for d, _ in price_rows]),
    )
    return float(compute_mdd(prices.to_frame("_t")).iloc[0])


class TestDcaN1IdentityWithBuyAndHold:
    """DCA(N=1) == buy-and-hold. 이게 깨지면 equity curve 구성 자체가 잘못된 것."""

    def test_rising_prices(self, monkeypatch):
        monkeypatch.setitem(DCA_INSTALLMENTS, "30d", 1)
        prices = [100.0, 110.0, 90.0, 130.0, 150.0]
        start = date(2026, 6, 1)
        price_rows = make_series(prices, start)

        dca = _compute_dca(price_rows, "30d", start, price_rows[-1][0])

        assert dca is not None
        assert dca.final_return_pct == pytest.approx(buy_and_hold_return(price_rows))
        assert dca.mdd_pct == pytest.approx(buy_and_hold_mdd(price_rows))
        assert dca.warning is None

    def test_falling_prices(self, monkeypatch):
        monkeypatch.setitem(DCA_INSTALLMENTS, "30d", 1)
        prices = [200.0, 180.0, 150.0, 160.0, 140.0]
        start = date(2026, 6, 1)
        price_rows = make_series(prices, start)

        dca = _compute_dca(price_rows, "30d", start, price_rows[-1][0])

        assert dca is not None
        assert dca.final_return_pct == pytest.approx(buy_and_hold_return(price_rows))
        assert dca.mdd_pct == pytest.approx(buy_and_hold_mdd(price_rows))


class TestDcaMultipleInstallments:
    """정상 DCA — buy-and-hold와 값이 갈라져야 한다."""

    def test_diverges_from_buy_and_hold(self, monkeypatch):
        monkeypatch.setitem(DCA_INSTALLMENTS, "30d", 4)
        # 30일간 우상향하지만 변동이 있는 가격
        prices = [100.0 + i * 2 - (5 if i % 3 == 0 else 0) for i in range(31)]
        start = date(2026, 6, 1)
        price_rows = make_series(prices, start)

        dca = _compute_dca(price_rows, "30d", start, price_rows[-1][0])
        bh_return = buy_and_hold_return(price_rows)

        assert dca is not None
        assert dca.warning is None  # 결손 없음 — 4회 전부 집행
        assert dca.final_return_pct != pytest.approx(bh_return)

    def test_dca_softens_mdd_when_volatility_is_early(self, monkeypatch):
        """변동(급락)이 매수 분산 초반부에 걸쳐 있으면 DCA의 MDD가 buy-and-hold보다 완화돼야 한다."""
        monkeypatch.setitem(DCA_INSTALLMENTS, "30d", 4)
        start = date(2026, 6, 1)
        # 초반에 -40% 급락 후 완만히 회복 — buy-and-hold는 급락을 전액 맞지만
        # DCA는 아직 미집행 원금이 현금으로 남아있어 급락의 충격이 줄어든다.
        prices = [100.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0]
        price_rows = [
            (start + timedelta(days=round(i * 30 / (len(prices) - 1))), p)
            for i, p in enumerate(prices)
        ]

        dca = _compute_dca(price_rows, "30d", start, price_rows[-1][0])
        bh_mdd = buy_and_hold_mdd(price_rows)

        assert dca is not None
        assert dca.mdd_pct > bh_mdd  # 덜 빠짐 (mdd는 음수이므로 완화될수록 값이 커짐/0에 가까워짐)


class TestDcaDeficitWindow:
    """상장일(시계열 시작)이 명목 구간 시작일보다 늦은 경우 — 일부 회차 스킵 + 경고."""

    def test_partial_execution_warns_with_counts(self, monkeypatch):
        monkeypatch.setitem(DCA_INSTALLMENTS, "1825d", 20)
        nominal_start = date(2021, 7, 7)
        actual_date = date(2026, 7, 6)
        # 실제 가격 데이터는 상장(수집 시작) 지연으로 2년 뒤부터 존재
        listing_date = date(2023, 7, 7)
        prices = [100.0 + i * 0.1 for i in range(1000)]
        price_rows = make_series(prices, listing_date)
        # actual_date를 넘는 여분 데이터는 제거해 실제 조회 결과처럼 만든다
        price_rows = [(d, p) for d, p in price_rows if d <= actual_date]

        dca = _compute_dca(price_rows, "1825d", nominal_start, actual_date)

        assert dca is not None
        assert dca.warning is not None
        assert "/20회" in dca.warning
        executed = int(dca.warning.split("/")[0])
        assert 0 < executed < 20

    def test_full_history_has_no_warning(self, monkeypatch):
        monkeypatch.setitem(DCA_INSTALLMENTS, "1825d", 20)
        nominal_start = date(2021, 7, 7)
        actual_date = date(2026, 7, 6)
        prices = [100.0 + i * 0.1 for i in range(1826)]
        price_rows = make_series(prices, nominal_start)
        price_rows = [(d, p) for d, p in price_rows if d <= actual_date]

        dca = _compute_dca(price_rows, "1825d", nominal_start, actual_date)

        assert dca is not None
        assert dca.warning is None


class TestDcaUnsupportedPeriods:
    """1d/7d는 분할이 성립하지 않아 항상 None."""

    @pytest.mark.parametrize("period", ["1d", "7d"])
    def test_no_dca_for_short_periods(self, period):
        prices = [100.0, 105.0]
        start = date(2026, 7, 5)
        price_rows = make_series(prices, start)

        dca = _compute_dca(price_rows, period, start, price_rows[-1][0])

        assert dca is None

    def test_insufficient_data_returns_none(self):
        price_rows = [(date(2026, 7, 6), 100.0)]  # 1행뿐 — 계산 불가
        dca = _compute_dca(price_rows, "30d", date(2026, 6, 6), date(2026, 7, 6))
        assert dca is None

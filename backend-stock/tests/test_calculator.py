"""
금융 계산 단위 테스트.

모든 케이스는 손으로 검산 가능한 고정 입력값을 사용한다.
금융 계산이 틀리면 서비스 전체 가치가 0이므로 각 공식을 독립적으로 검증한다.
"""

import numpy as np
import pandas as pd
import pytest

from fomobot.services.calculator import (
    compute_excess_return,
    compute_mdd,
    compute_quote_metrics,
    compute_returns,
    compute_volatility,
    build_ranking_df,
)


def make_price_matrix(data: dict, dates: list[str]) -> pd.DataFrame:
    """테스트용 가격 행렬 생성 헬퍼."""
    idx = pd.DatetimeIndex(dates)
    return pd.DataFrame(data, index=idx)


# ── compute_returns ───────────────────────────────────────────────────────────

class TestComputeReturns:
    def test_simple_two_day(self):
        """100 → 110: 수익률 = (110/100 - 1) × 100 = 10.0%"""
        pm = make_price_matrix({"A": [100.0, 110.0]}, ["2024-01-01", "2024-01-02"])
        result = compute_returns(pm)
        assert result["A"] == pytest.approx(10.0)

    def test_negative_return(self):
        """100 → 80: 수익률 = (80/100 - 1) × 100 = -20.0%"""
        pm = make_price_matrix({"A": [100.0, 80.0]}, ["2024-01-01", "2024-01-02"])
        result = compute_returns(pm)
        assert result["A"] == pytest.approx(-20.0)

    def test_multiple_tickers(self):
        """
        A: 100 → 150  = +50%
        B: 200 → 180  = -10%
        C: 50  → 75   = +50%
        """
        pm = make_price_matrix(
            {"A": [100.0, 150.0], "B": [200.0, 180.0], "C": [50.0, 75.0]},
            ["2024-01-01", "2024-01-05"],
        )
        result = compute_returns(pm)
        assert result["A"] == pytest.approx(50.0)
        assert result["B"] == pytest.approx(-10.0)
        assert result["C"] == pytest.approx(50.0)

    def test_five_day_series(self):
        """
        100 → 102 → 99 → 105 → 110
        수익률 = (110/100 - 1) × 100 = 10.0%  (중간값 무관)
        """
        prices = [100.0, 102.0, 99.0, 105.0, 110.0]
        dates = pd.date_range("2024-01-01", periods=5)
        pm = pd.DataFrame({"A": prices}, index=dates)
        result = compute_returns(pm)
        assert result["A"] == pytest.approx(10.0)

    def test_empty_dataframe(self):
        result = compute_returns(pd.DataFrame())
        assert result.empty

    def test_single_row_returns_empty(self):
        pm = make_price_matrix({"A": [100.0]}, ["2024-01-01"])
        result = compute_returns(pm)
        assert result.empty


# ── compute_mdd ───────────────────────────────────────────────────────────────

class TestComputeMDD:
    def test_no_drawdown(self):
        """단조 상승: 100 → 110 → 120 → 130, MDD = 0%"""
        prices = [100.0, 110.0, 120.0, 130.0]
        dates = pd.date_range("2024-01-01", periods=4)
        pm = pd.DataFrame({"A": prices}, index=dates)
        result = compute_mdd(pm)
        assert result["A"] == pytest.approx(0.0, abs=1e-9)

    def test_known_drawdown(self):
        """
        100 → 120 → 90 → 110
        고점=120, 저점=90
        MDD = (90-120)/120 × 100 = -25.0%
        """
        prices = [100.0, 120.0, 90.0, 110.0]
        dates = pd.date_range("2024-01-01", periods=4)
        pm = pd.DataFrame({"A": prices}, index=dates)
        result = compute_mdd(pm)
        assert result["A"] == pytest.approx(-25.0)

    def test_mdd_from_initial_peak(self):
        """
        120 → 60 → 90
        고점=120, MDD = (60-120)/120 × 100 = -50.0%
        """
        prices = [120.0, 60.0, 90.0]
        dates = pd.date_range("2024-01-01", periods=3)
        pm = pd.DataFrame({"A": prices}, index=dates)
        result = compute_mdd(pm)
        assert result["A"] == pytest.approx(-50.0)

    def test_multiple_drawdowns_picks_worst(self):
        """
        두 번의 낙폭 중 더 큰 것을 선택.
        100 → 80 (-20%) → 90 → 60 (-33.3%) → 95
        두 번째 낙폭: (60-90)/90 = -33.3%
        """
        prices = [100.0, 80.0, 90.0, 60.0, 95.0]
        dates = pd.date_range("2024-01-01", periods=5)
        pm = pd.DataFrame({"A": prices}, index=dates)
        result = compute_mdd(pm)
        # 전체 누적고점 기준: 고점=100, min drawdown = (60-100)/100 = -40%
        assert result["A"] == pytest.approx(-40.0)

    def test_mdd_is_non_positive(self):
        """MDD는 항상 0 이하."""
        prices = [100.0, 105.0, 95.0, 110.0, 85.0]
        dates = pd.date_range("2024-01-01", periods=5)
        pm = pd.DataFrame({"A": prices}, index=dates)
        result = compute_mdd(pm)
        assert result["A"] <= 0


# ── compute_volatility ────────────────────────────────────────────────────────

class TestComputeVolatility:
    def test_zero_volatility(self):
        """가격이 일정하면 변동성 = 0."""
        prices = [100.0, 100.0, 100.0, 100.0, 100.0]
        dates = pd.date_range("2024-01-01", periods=5)
        pm = pd.DataFrame({"A": prices}, index=dates)
        result = compute_volatility(pm)
        assert result["A"] == pytest.approx(0.0, abs=1e-9)

    def test_known_volatility(self):
        """
        일간 수익률: +10%, -10%, +10%, -10%  (prices: 100, 110, 99, 108.9, 98.01)
        std(daily_ret) ≈ 0.1  (정확히는 [0.1, -0.0909..., 0.1, -0.0909...])
        연율화 = std × sqrt(252) × 100
        """
        prices = [100.0, 110.0, 99.0, 108.9, 98.01]
        dates = pd.date_range("2024-01-01", periods=5)
        pm = pd.DataFrame({"A": prices}, index=dates)
        result = compute_volatility(pm)
        # 수기 계산
        import numpy as np
        daily = pd.Series(prices).pct_change().dropna()
        expected = daily.std() * np.sqrt(252) * 100
        assert result["A"] == pytest.approx(expected, rel=1e-6)

    def test_volatility_is_non_negative(self):
        prices = [100.0, 95.0, 105.0, 100.0, 110.0]
        dates = pd.date_range("2024-01-01", periods=5)
        pm = pd.DataFrame({"A": prices}, index=dates)
        result = compute_volatility(pm)
        assert result["A"] >= 0


# ── compute_excess_return ─────────────────────────────────────────────────────

class TestComputeExcessReturn:
    def test_simple_excess(self):
        """
        종목 A: +20%, 지수: +10%  →  초과수익 = +10%
        종목 B: +5%,  지수: +10%  →  초과수익 = -5%
        """
        stock_returns = pd.Series({"A": 20.0, "B": 5.0})
        index_series = pd.Series(
            [100.0, 110.0],
            index=pd.DatetimeIndex(["2024-01-01", "2024-01-31"]),
        )
        result = compute_excess_return(stock_returns, index_series)
        assert result["A"] == pytest.approx(10.0)
        assert result["B"] == pytest.approx(-5.0)

    def test_index_flat(self):
        """지수 수익률 0% → 초과수익 = 종목 수익률 그대로."""
        stock_returns = pd.Series({"A": 15.0})
        index_series = pd.Series(
            [100.0, 100.0],
            index=pd.DatetimeIndex(["2024-01-01", "2024-01-31"]),
        )
        result = compute_excess_return(stock_returns, index_series)
        assert result["A"] == pytest.approx(15.0)

    def test_empty_index_returns_nan(self):
        stock_returns = pd.Series({"A": 10.0})
        result = compute_excess_return(stock_returns, pd.Series(dtype=float))
        assert np.isnan(result["A"])


# ── build_ranking_df ──────────────────────────────────────────────────────────

class TestBuildRankingDf:
    def test_ranking_order(self):
        """수익률 내림차순 정렬 및 rank 컬럼 검증."""
        dates = pd.date_range("2024-01-01", periods=2)
        pm = pd.DataFrame(
            {"A": [100.0, 130.0], "B": [100.0, 150.0], "C": [100.0, 110.0]},
            index=dates,
        )
        index_series = pd.Series([100.0, 100.0], index=dates)
        result = build_ranking_df(pm, index_series, top=3)

        assert list(result["ticker"]) == ["B", "A", "C"]
        assert list(result["rank"]) == [1, 2, 3]

    def test_top_n_limits_rows(self):
        """top=2이면 결과 행 수 ≤ 2."""
        dates = pd.date_range("2024-01-01", periods=2)
        pm = pd.DataFrame(
            {"A": [100.0, 130.0], "B": [100.0, 150.0], "C": [100.0, 110.0]},
            index=dates,
        )
        index_series = pd.Series([100.0, 100.0], index=dates)
        result = build_ranking_df(pm, index_series, top=2)
        assert len(result) == 2

    def test_result_has_required_columns(self):
        dates = pd.date_range("2024-01-01", periods=2)
        pm = pd.DataFrame({"A": [100.0, 110.0]}, index=dates)
        index_series = pd.Series([100.0, 105.0], index=dates)
        result = build_ranking_df(pm, index_series, top=5)

        required = {"rank", "ticker", "return_pct", "mdd_pct",
                    "volatility_annualized_pct", "excess_return_pct"}
        assert required.issubset(result.columns)


# ── compute_quote_metrics ─────────────────────────────────────────────────────

class TestComputeQuoteMetrics:
    def test_compute_quote_metrics_normal(self):
        """정상적인 가격 시리즈를 입력했을 때 지표들이 올바르게 계산되는지 확인"""
        prices = [100.0, 110.0, 99.0, 108.9, 98.01]
        dates = pd.date_range("2024-01-01", periods=5)
        series = pd.Series(prices, index=dates)

        result = compute_quote_metrics(series)

        # 수익률 검증: 100 -> 98.01 이므로 -1.99%
        assert result["return_pct"] == pytest.approx(-1.99)

        # MDD 검증: 최고점 110 -> 최저점 98.01 (또는 99), (98.01 - 110) / 110 * 100 = -10.9%
        assert result["mdd_pct"] == pytest.approx(-10.9)

        # Volatility 검증:
        daily = series.pct_change().dropna()
        expected_vol = daily.std() * np.sqrt(252) * 100
        assert result["volatility_annualized_pct"] == pytest.approx(expected_vol, rel=1e-6)

    def test_compute_quote_metrics_empty(self):
        """빈 시리즈를 입력했을 때 None을 반환하는지 확인"""
        series = pd.Series(dtype=float)
        result = compute_quote_metrics(series)

        assert result == {
            "return_pct": None,
            "mdd_pct": None,
            "volatility_annualized_pct": None,
        }

    def test_compute_quote_metrics_single(self):
        """데이터가 1개인 시리즈를 입력했을 때 None을 반환하는지 확인"""
        series = pd.Series([100.0], index=pd.DatetimeIndex(["2024-01-01"]))
        result = compute_quote_metrics(series)

        assert result == {
            "return_pct": None,
            "mdd_pct": None,
            "volatility_annualized_pct": None,
        }

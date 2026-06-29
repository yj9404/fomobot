"""
노이즈 필터 단위 테스트.
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from fomobot.services.noise_filter import (
    apply_kospi_filter,
    apply_nasdaq_filter,
    drop_low_data_tickers,
)


@pytest.fixture
def mock_settings():
    with patch("fomobot.services.noise_filter.settings") as mock:
        # KOSPI settings
        mock.kospi_min_market_cap = 1000
        mock.kospi_min_avg_volume_30d = 100
        mock.kospi_min_price = 10

        # NASDAQ settings
        mock.nasdaq_min_market_cap_usd = 500
        mock.nasdaq_min_avg_volume_30d_usd = 50
        mock.nasdaq_min_price_usd = 5.0

        yield mock


class TestApplyKospiFilter:
    def test_pass_all_conditions(self, mock_settings):
        df = pd.DataFrame({
            "ticker": ["A", "B"],
            "market_cap": [1000, 2000],       # >= 1000
            "avg_volume_30d": [100, 150],     # >= 100
            "close_adj": [10, 20],            # >= 10
        })
        result = apply_kospi_filter(df)
        assert len(result) == 2
        assert list(result["ticker"]) == ["A", "B"]

    def test_filter_by_market_cap(self, mock_settings):
        df = pd.DataFrame({
            "ticker": ["PASS", "FAIL"],
            "market_cap": [1000, 999],        # FAIL is < 1000
            "avg_volume_30d": [100, 100],
            "close_adj": [10, 10],
        })
        result = apply_kospi_filter(df)
        assert len(result) == 1
        assert list(result["ticker"]) == ["PASS"]

    def test_filter_by_avg_volume(self, mock_settings):
        df = pd.DataFrame({
            "ticker": ["PASS", "FAIL"],
            "market_cap": [1000, 1000],
            "avg_volume_30d": [100, 99],      # FAIL is < 100
            "close_adj": [10, 10],
        })
        result = apply_kospi_filter(df)
        assert len(result) == 1
        assert list(result["ticker"]) == ["PASS"]

    def test_filter_by_close_adj(self, mock_settings):
        df = pd.DataFrame({
            "ticker": ["PASS", "FAIL"],
            "market_cap": [1000, 1000],
            "avg_volume_30d": [100, 100],
            "close_adj": [10, 9],             # FAIL is < 10
        })
        result = apply_kospi_filter(df)
        assert len(result) == 1
        assert list(result["ticker"]) == ["PASS"]


class TestApplyNasdaqFilter:
    def test_pass_all_conditions(self, mock_settings):
        df = pd.DataFrame({
            "ticker": ["AAPL", "MSFT"],
            "market_cap": [500, 1000],       # >= 500
            "avg_volume_30d": [50, 100],     # >= 50
            "close_adj": [5.0, 10.0],        # >= 5.0
        })
        result = apply_nasdaq_filter(df)
        assert len(result) == 2
        assert list(result["ticker"]) == ["AAPL", "MSFT"]

    def test_market_cap_zero_bypasses_check(self, mock_settings):
        """market_cap이 0인 경우 시총 검사를 통과해야 한다."""
        df = pd.DataFrame({
            "ticker": ["ZERO_CAP", "LOW_CAP"],
            "market_cap": [0, 499],          # ZERO_CAP=0 (pass), LOW_CAP=499 (fail)
            "avg_volume_30d": [50, 50],
            "close_adj": [5.0, 5.0],
        })
        result = apply_nasdaq_filter(df)
        assert len(result) == 1
        assert list(result["ticker"]) == ["ZERO_CAP"]

    def test_filter_by_avg_volume(self, mock_settings):
        df = pd.DataFrame({
            "ticker": ["PASS", "FAIL"],
            "market_cap": [500, 500],
            "avg_volume_30d": [50, 49],      # FAIL is < 50
            "close_adj": [5.0, 5.0],
        })
        result = apply_nasdaq_filter(df)
        assert len(result) == 1
        assert list(result["ticker"]) == ["PASS"]

    def test_filter_by_close_adj(self, mock_settings):
        df = pd.DataFrame({
            "ticker": ["PASS", "FAIL"],
            "market_cap": [500, 500],
            "avg_volume_30d": [50, 50],
            "close_adj": [5.0, 4.9],         # FAIL is < 5.0
        })
        result = apply_nasdaq_filter(df)
        assert len(result) == 1
        assert list(result["ticker"]) == ["PASS"]


class TestDropLowDataTickers:
    def test_no_missing_data(self):
        dates = pd.date_range("2024-01-01", periods=5)
        df = pd.DataFrame({
            "A": [1, 2, 3, 4, 5],
            "B": [10, 20, 30, 40, 50]
        }, index=dates)

        result = drop_low_data_tickers(df, max_missing_ratio=0.2)
        assert len(result.columns) == 2
        assert list(result.columns) == ["A", "B"]

    def test_drops_above_threshold(self):
        dates = pd.date_range("2024-01-01", periods=5)
        # 5일 중 결측치 개수:
        # A: 0/5 = 0% missing
        # B: 1/5 = 20% missing
        # C: 2/5 = 40% missing
        df = pd.DataFrame({
            "A": [1.0, 2.0, 3.0, 4.0, 5.0],
            "B": [10.0, np.nan, 30.0, 40.0, 50.0],
            "C": [100.0, np.nan, np.nan, 400.0, 500.0]
        }, index=dates)

        # 임계값 20% (0.2)
        result = drop_low_data_tickers(df, max_missing_ratio=0.2)
        assert len(result.columns) == 2
        assert list(result.columns) == ["A", "B"]

    def test_all_missing(self):
        dates = pd.date_range("2024-01-01", periods=5)
        df = pd.DataFrame({
            "A": [np.nan] * 5,
        }, index=dates)

        result = drop_low_data_tickers(df, max_missing_ratio=0.5)
        assert len(result.columns) == 0

    def test_custom_threshold(self):
        dates = pd.date_range("2024-01-01", periods=10)
        # A: 3/10 = 30% missing
        df = pd.DataFrame({
            "A": [1.0] * 7 + [np.nan] * 3,
        }, index=dates)

        # 0.25 (25%) -> fail
        result1 = drop_low_data_tickers(df, max_missing_ratio=0.25)
        assert len(result1.columns) == 0

        # 0.35 (35%) -> pass
        result2 = drop_low_data_tickers(df, max_missing_ratio=0.35)
        assert len(result2.columns) == 1

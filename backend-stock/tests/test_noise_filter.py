"""
노이즈 필터 단위 테스트.

apply_nasdaq_filter의 market_cap 로직과
apply_price_sanity_filter의 corporate action 감지를 검증한다.
"""

import pandas as pd

from fomobot.services.noise_filter import apply_nasdaq_filter, apply_price_sanity_filter


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def make_meta(tickers: list[str], market_cap: list[float], avg_volume: list[float], close_adj: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "ticker": tickers,
        "market_cap": market_cap,
        "avg_volume_30d": avg_volume,
        "close_adj": close_adj,
    })


def make_price_matrix(data: dict, n_days: int = 10) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n_days)
    return pd.DataFrame(data, index=dates)


# ── apply_nasdaq_filter: market_cap 로직 ──────────────────────────────────────

class TestNasdaqMarketCapFilter:
    def test_known_large_cap_passes(self, monkeypatch):
        """시총이 임계값($5억) 이상이면 통과."""
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_exclude_unknown_market_cap", False)
        monkeypatch.setattr(settings, "nasdaq_min_market_cap_usd", 500_000_000)
        monkeypatch.setattr(settings, "nasdaq_min_avg_volume_30d_usd", 0)
        monkeypatch.setattr(settings, "nasdaq_min_price_usd", 0.0)

        df = make_meta(["NVDA"], [600_000_000], [10_000_000], [500.0])
        result = apply_nasdaq_filter(df)
        assert "NVDA" in result["ticker"].values

    def test_small_cap_excluded(self, monkeypatch):
        """시총 $30만(PAVS급) 종목은 임계값 미달로 제외 — 단, market_cap이 실제로 수집된 경우."""
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_exclude_unknown_market_cap", False)
        monkeypatch.setattr(settings, "nasdaq_min_market_cap_usd", 500_000_000)
        monkeypatch.setattr(settings, "nasdaq_min_avg_volume_30d_usd", 0)
        monkeypatch.setattr(settings, "nasdaq_min_price_usd", 0.0)

        df = make_meta(["PAVS"], [300_000], [5_000_000], [100.0])
        result = apply_nasdaq_filter(df)
        assert "PAVS" not in result["ticker"].values

    def test_unknown_market_cap_passes_when_flag_false(self, monkeypatch):
        """nasdaq_exclude_unknown_market_cap=False일 때 market_cap=0이면 시총 조건 생략 → 통과."""
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_exclude_unknown_market_cap", False)
        monkeypatch.setattr(settings, "nasdaq_min_market_cap_usd", 500_000_000)
        monkeypatch.setattr(settings, "nasdaq_min_avg_volume_30d_usd", 0)
        monkeypatch.setattr(settings, "nasdaq_min_price_usd", 0.0)

        df = make_meta(["UNKNOWN"], [0], [10_000_000], [50.0])
        result = apply_nasdaq_filter(df)
        assert "UNKNOWN" in result["ticker"].values

    def test_unknown_market_cap_excluded_when_flag_true(self, monkeypatch):
        """nasdaq_exclude_unknown_market_cap=True일 때 market_cap=0이면 보수적으로 제외."""
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_exclude_unknown_market_cap", True)
        monkeypatch.setattr(settings, "nasdaq_min_market_cap_usd", 500_000_000)
        monkeypatch.setattr(settings, "nasdaq_min_avg_volume_30d_usd", 0)
        monkeypatch.setattr(settings, "nasdaq_min_price_usd", 0.0)

        df = make_meta(["UNKNOWN"], [0], [10_000_000], [50.0])
        result = apply_nasdaq_filter(df)
        assert "UNKNOWN" not in result["ticker"].values

    def test_known_large_cap_passes_when_flag_true(self, monkeypatch):
        """nasdaq_exclude_unknown_market_cap=True여도 실제 시총이 있으면 통과."""
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_exclude_unknown_market_cap", True)
        monkeypatch.setattr(settings, "nasdaq_min_market_cap_usd", 500_000_000)
        monkeypatch.setattr(settings, "nasdaq_min_avg_volume_30d_usd", 0)
        monkeypatch.setattr(settings, "nasdaq_min_price_usd", 0.0)

        df = make_meta(["AAPL"], [3_000_000_000_000], [50_000_000], [180.0])
        result = apply_nasdaq_filter(df)
        assert "AAPL" in result["ticker"].values


# ── apply_price_sanity_filter ─────────────────────────────────────────────────

class TestPriceSanityFilter:
    def test_normal_stocks_pass(self, monkeypatch):
        """NVDA·AAPL 수준의 정상 주가 흐름은 필터를 통과한다."""
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_max_daily_move_pct", 3.0)
        monkeypatch.setattr(settings, "nasdaq_max_volatility_pct", 1000.0)

        # 최대 일간 변동 ≈ 3% 수준의 정상 주가
        prices_nvda = [100.0 * (1 + 0.02 * (i % 3 - 1)) for i in range(10)]
        prices_aapl = [180.0 * (1 + 0.01 * (i % 2)) for i in range(10)]
        pm = make_price_matrix({"NVDA": prices_nvda, "AAPL": prices_aapl}, n_days=10)

        result = apply_price_sanity_filter(pm)
        assert "NVDA" in result.columns
        assert "AAPL" in result.columns

    def test_reverse_split_ticker_excluded(self, monkeypatch):
        """
        1대100 액면병합 시뮬레이션:
        6일간 $1로 거래되다가 병합 당일 $100으로 점프 (pct_change = 99 = 9900%).
        nasdaq_max_daily_move_pct=3.0 기준 초과 → 제외.
        """
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_max_daily_move_pct", 3.0)
        monkeypatch.setattr(settings, "nasdaq_max_volatility_pct", 1000.0)

        # PAVS: 병합 전 $1, 병합 당일 $100
        prices_pavs = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 100.0, 100.0, 100.0, 100.0]
        prices_nvda = [500.0, 505.0, 498.0, 510.0, 503.0, 507.0, 500.0, 512.0, 508.0, 515.0]
        pm = make_price_matrix({"PAVS": prices_pavs, "NVDA": prices_nvda}, n_days=10)

        result = apply_price_sanity_filter(pm)
        assert "PAVS" not in result.columns
        assert "NVDA" in result.columns

    def test_forward_split_not_triggered(self, monkeypatch):
        """
        1대10 정방향 액면분할은 yfinance auto_adjust=True로 소급 조정되므로
        실제 데이터에서는 가격 점프가 나타나지 않는다.
        설령 조정 전 raw 데이터에서 -90% 하락이 있더라도
        pct_change 절댓값 = 0.9 < 3.0 임계값이므로 이 필터의 대상이 아니다
        (주가는 최대 -100%까지만 하락하므로 하향으로는 임계값 초과 불가).
        """
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_max_daily_move_pct", 3.0)
        monkeypatch.setattr(settings, "nasdaq_max_volatility_pct", 1000.0)

        prices_split = [100.0, 100.0, 100.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        pm = make_price_matrix({"SPLIT": prices_split}, n_days=10)

        # 하락(-90%)은 abs(pct_change)=0.9 < 3.0 → 통과(제거 안 됨)
        result = apply_price_sanity_filter(pm)
        assert "SPLIT" in result.columns

    def test_extreme_upward_spike_excluded(self, monkeypatch):
        """
        하루 만에 주가가 5배로 급등(+400% = pct_change 4.0)하는 경우 제외.
        역방향 스플릿 왜곡의 전형적인 패턴.
        """
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_max_daily_move_pct", 3.0)
        monkeypatch.setattr(settings, "nasdaq_max_volatility_pct", 1000.0)

        prices_spike = [10.0, 10.0, 10.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
        pm = make_price_matrix({"SPIKE": prices_spike}, n_days=10)

        result = apply_price_sanity_filter(pm)
        assert "SPIKE" not in result.columns

    def test_high_volatility_excluded_by_secondary_filter(self, monkeypatch):
        """
        일간 변동률은 임계값 이하이지만 연율화 변동성이 1000%를 초과하는 종목을 제외.
        매일 250% 수익률이 반복되면 변동성이 극도로 높아진다.
        """
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_max_daily_move_pct", 3.0)
        monkeypatch.setattr(settings, "nasdaq_max_volatility_pct", 1000.0)

        # 매일 ±250% 수준의 극단적 변동 (임계값 3.0 미만이지만 변동성 폭발)
        # 실제로 2.5 = 250%도 max_daily_move_pct=3.0 기준으로는 통과
        # (테스트 재현용 난수 생성, 통계적인 극단 케이스 검증)
        import numpy as np
        rng = np.random.default_rng(42)
        prices = [100.0]
        for _ in range(29):
            change = rng.choice([2.5, -0.70])  # 250% 상승 or 70% 하락 반복 → vol 폭발
            prices.append(prices[-1] * (1 + change))
        dates = pd.date_range("2024-01-01", periods=30)
        pm = pd.DataFrame({"VOLATILE": prices}, index=dates)

        result = apply_price_sanity_filter(pm)
        assert "VOLATILE" not in result.columns

    def test_empty_dataframe_returns_empty(self, monkeypatch):
        """빈 DataFrame은 그대로 반환."""
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_max_daily_move_pct", 3.0)
        monkeypatch.setattr(settings, "nasdaq_max_volatility_pct", 1000.0)

        result = apply_price_sanity_filter(pd.DataFrame())
        assert result.empty

    def test_single_row_returns_unchanged(self, monkeypatch):
        """단일 행(pct_change 계산 불가)은 그대로 반환."""
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_max_daily_move_pct", 3.0)
        monkeypatch.setattr(settings, "nasdaq_max_volatility_pct", 1000.0)

        pm = make_price_matrix({"A": [100.0]}, n_days=1)
        result = apply_price_sanity_filter(pm)
        assert "A" in result.columns

    def test_all_normal_tickers_preserved(self, monkeypatch):
        """정상 종목 여러 개는 모두 보존된다."""
        from fomobot.config import settings
        monkeypatch.setattr(settings, "nasdaq_max_daily_move_pct", 3.0)
        monkeypatch.setattr(settings, "nasdaq_max_volatility_pct", 1000.0)

        tickers = {
            "AAPL": [180 + i * 0.5 for i in range(10)],
            "MSFT": [300 + i * 1.0 for i in range(10)],
            "GOOGL": [150 - i * 0.3 for i in range(10)],
        }
        pm = make_price_matrix(tickers, n_days=10)
        result = apply_price_sanity_filter(pm)
        for ticker in tickers:
            assert ticker in result.columns

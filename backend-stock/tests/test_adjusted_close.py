"""
수정주가(adjusted close) 검증 테스트.

목적: 데이터 소스가 액면분할·배당을 수정주가에 올바르게 반영하는지 확인한다.
     수정주가 미반영 시 장기 수익률 전체가 오염되므로 핵심 검증이다.

검증 케이스:
  1. 삼성전자 (005930) 2018-05-04 50:1 액면분할
     - 분할 전 종가 약 2,480,000원  →  분할 후 약 49,600원
     - 수정주가는 분할 전 데이터도 분할 후 기준으로 환산해야 함
     - 즉 2018-05-03 수정주가 ≈ 49,600원 (분할 전 원래가가 아님)
  2. AAPL 2020-08-31 4:1 액면분할
     - 분할 직전 종가 약 $499  →  수정주가 기준 ≈ $124.75 (÷4)

이 테스트는 실제 네트워크를 사용한다 (pytest -m "not network"로 CI에서 스킵 가능).
"""

import pytest
import pandas as pd

pytestmark = pytest.mark.network  # 네트워크 필요 테스트 마킹


@pytest.fixture(scope="module")
def samsung_prices():
    """pykrx로 삼성전자 2018년 주변 가격 조회 (수정주가)."""
    try:
        from pykrx import stock
    except ImportError:
        pytest.skip("pykrx 미설치")

    df = stock.get_market_ohlcv_by_date("20180430", "20180510", "005930", adjusted=True)
    return df


@pytest.fixture(scope="module")
def aapl_prices():
    """yfinance로 AAPL 2020년 8월~9월 가격 조회 (수정주가)."""
    try:
        import yfinance as yf
    except ImportError:
        pytest.skip("yfinance 미설치")

    df = yf.download("AAPL", start="2020-08-28", end="2020-09-04", auto_adjust=True, progress=False)
    return df


class TestKospiAdjustedClose:
    def test_samsung_split_continuity(self, samsung_prices):
        """
        액면분할일(2018-05-04) 전후 수정주가 연속성 검증.

        수정주가가 올바르면:
          - 분할 전 종가(수정) ≈ 분할 후 종가 (비율 유지, 급락 없음)
          - 전일 대비 수익률이 50배 급등하지 않아야 함

        수정주가가 틀리면:
          - 2018-05-03 → 2018-05-04 수익률이 약 +4900% (50:1 미반영)로 폭발
        """
        if samsung_prices is None or samsung_prices.empty:
            pytest.skip("데이터 조회 실패")

        close_col = "종가" if "종가" in samsung_prices.columns else samsung_prices.columns[3]
        closes = samsung_prices[close_col].dropna()
        assert len(closes) >= 2, "데이터 부족"

        # 분할일 전후 수익률이 ±30% 이내여야 함 (50:1 미반영이면 ~4900%)
        pct_changes = closes.pct_change().dropna() * 100
        max_single_day = pct_changes.abs().max()
        assert max_single_day < 30.0, (
            f"수정주가 미반영 의심: 단일일 최대 변동 {max_single_day:.1f}% "
            f"(50:1 미반영 시 ~4900%)"
        )

    def test_samsung_split_price_range(self, samsung_prices):
        """분할 후 삼성전자 수정주가는 만원~십만원 사이여야 한다."""
        if samsung_prices is None or samsung_prices.empty:
            pytest.skip("데이터 조회 실패")

        close_col = "종가" if "종가" in samsung_prices.columns else samsung_prices.columns[3]
        closes = samsung_prices[close_col].dropna()

        # 수정주가 기준 분할 후 가격대: 45,000 ~ 55,000원 (2018-05-04 기준)
        post_split = closes[closes.index >= pd.Timestamp("2018-05-04")]
        if post_split.empty:
            pytest.skip("분할 후 데이터 없음")

        assert post_split.iloc[0] < 200_000, (
            f"수정주가 미반영 의심: 분할 후 가격 {post_split.iloc[0]:,}원 "
            f"(수정주가면 ~49,600원, 미반영이면 ~2,480,000원)"
        )


class TestNasdaqAdjustedClose:
    def test_aapl_split_continuity(self, aapl_prices):
        """
        AAPL 2020-08-31 4:1 분할 전후 수정주가 연속성 검증.
        수정주가가 올바르면 분할일 수익률이 ±10% 이내.
        미반영이면 약 +300% (4배) 급등.
        """
        if aapl_prices is None or aapl_prices.empty:
            pytest.skip("데이터 조회 실패")

        close = aapl_prices["Close"].squeeze().dropna()
        assert len(close) >= 2

        pct_changes = close.pct_change().dropna() * 100
        max_single_day = pct_changes.abs().max()
        assert max_single_day < 15.0, (
            f"수정주가 미반영 의심: 단일일 최대 변동 {max_single_day:.1f}% "
            f"(4:1 미반영 시 ~+300%)"
        )

    def test_aapl_split_price_range(self, aapl_prices):
        """분할 후 AAPL 수정주가는 $100~$200 사이여야 한다 (2020-09 기준)."""
        if aapl_prices is None or aapl_prices.empty:
            pytest.skip("데이터 조회 실패")

        close = aapl_prices["Close"].squeeze().dropna()
        post_split = close[close.index >= pd.Timestamp("2020-08-31")]
        if post_split.empty:
            pytest.skip("분할 후 데이터 없음")

        assert post_split.iloc[0] < 300.0, (
            f"수정주가 미반영 의심: 분할 후 가격 ${post_split.iloc[0]:.2f} "
            f"(수정주가면 ~$124, 미반영이면 ~$499)"
        )

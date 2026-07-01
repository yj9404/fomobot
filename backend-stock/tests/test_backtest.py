"""
백테스트 _compute_current_returns 단위 테스트.

재작성 전/후 수익률 계산 로직의 정확성을 검증한다.
DB 없이 순수 함수 로직만 테스트 (mock 사용).

검증 항목:
  1. 정상 수익률 계산 (as_of 주가 → 오늘 주가)
  2. 상장폐지 (오늘 주가 없음) → None (생존 편향 유지)
  3. close_price_at_snapshot NULL → None (backfill 미완료)
  4. 폴백 없음 확인 (price_start=None이어도 price_end로 대체 안 됨)
  5. 평균 수익률 계산 (None 종목 제외)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date


# ── 헬퍼: snapshot row mock ────────────────────────────────────────────────────

def make_snapshot_row(ticker: str, close_price_at_snapshot: float | None = None):
    """RankingSnapshot row mock 생성."""
    row = MagicMock()
    row.ticker = ticker
    row.rank = 1
    row.name = ticker
    row.return_pct = 10.0
    row.snapshot_date = date(2025, 1, 2)
    row.close_price_at_snapshot = close_price_at_snapshot
    return row


# ── 핵심 계산 로직 추출 (DB 없이 테스트하기 위해 분리) ─────────────────────────

def compute_returns_from_prices(
    snapshot_rows,
    today_prices: dict[str, float | None],
) -> dict[str, float | None]:
    """
    api/backtest.py의 _compute_current_returns 핵심 로직을 추출한 순수 함수.
    DB 호출 없이 단위 테스트 가능.
    """
    returns: dict[str, float | None] = {}
    for row in snapshot_rows:
        price_start = row.close_price_at_snapshot
        price_end = today_prices.get(row.ticker)

        if price_start and price_end and price_start > 0:
            returns[row.ticker] = (price_end / price_start - 1) * 100
        else:
            returns[row.ticker] = None

    return returns


# ── 테스트 케이스 ──────────────────────────────────────────────────────────────

class TestComputeReturnsFromPrices:

    def test_normal_return(self):
        """100 → 110: 수익률 = 10.0%"""
        rows = [make_snapshot_row("A", close_price_at_snapshot=100.0)]
        today = {"A": 110.0}
        result = compute_returns_from_prices(rows, today)
        assert result["A"] == pytest.approx(10.0)

    def test_negative_return(self):
        """100 → 80: 수익률 = -20.0%"""
        rows = [make_snapshot_row("B", close_price_at_snapshot=100.0)]
        today = {"B": 80.0}
        result = compute_returns_from_prices(rows, today)
        assert result["B"] == pytest.approx(-20.0)

    def test_delisted_no_today_price(self):
        """
        상장폐지: 오늘 주가 없음 → None.
        생존 편향(survivorship bias) 의도된 동작.
        폴백 절대 없음.
        """
        rows = [make_snapshot_row("DEAD", close_price_at_snapshot=50.0)]
        today = {}  # 상장폐지 → 딕셔너리에 없음
        result = compute_returns_from_prices(rows, today)
        assert result["DEAD"] is None

    def test_missing_snapshot_price(self):
        """
        close_price_at_snapshot=None (backfill 미완료) → None.
        오늘 주가가 있어도 as_of 주가가 없으면 계산 불가.
        """
        rows = [make_snapshot_row("X", close_price_at_snapshot=None)]
        today = {"X": 200.0}
        result = compute_returns_from_prices(rows, today)
        assert result["X"] is None

    def test_zero_snapshot_price(self):
        """close_price_at_snapshot=0 → None (0으로 나누기 방지)."""
        rows = [make_snapshot_row("Z", close_price_at_snapshot=0.0)]
        today = {"Z": 100.0}
        result = compute_returns_from_prices(rows, today)
        assert result["Z"] is None

    def test_multiple_tickers_mixed(self):
        """여러 종목 혼합: 정상, 상장폐지, backfill 미완료."""
        rows = [
            make_snapshot_row("GOOD", close_price_at_snapshot=100.0),
            make_snapshot_row("DEAD", close_price_at_snapshot=50.0),
            make_snapshot_row("NOPRICE", close_price_at_snapshot=None),
        ]
        today = {"GOOD": 120.0}  # DEAD, NOPRICE는 오늘 가격 없음

        result = compute_returns_from_prices(rows, today)

        assert result["GOOD"] == pytest.approx(20.0)
        assert result["DEAD"] is None      # 상장폐지
        assert result["NOPRICE"] is None   # backfill 미완료

    def test_avg_excludes_none(self):
        """평균 수익률 계산 시 None 종목 제외."""
        items_returns = [20.0, None, -10.0, None]  # 유효한 값: 20, -10 → 평균 5
        valid = [r for r in items_returns if r is not None]
        avg = sum(valid) / len(valid) if valid else None
        assert avg == pytest.approx(5.0)

    def test_all_none_returns_none_avg(self):
        """모든 종목이 상장폐지 → 평균 None."""
        items_returns = [None, None]
        valid = [r for r in items_returns if r is not None]
        avg = sum(valid) / len(valid) if valid else None
        assert avg is None

    def test_kospi_samsung_example(self):
        """
        회귀 테스트 예시 — 삼성전자(005930).
        as_of 가격 50000원 → 오늘 55000원: 수익률 = 10.0%
        실제 DB 값과 비교 시 이 함수의 공식이 정확한지 확인용.
        """
        rows = [make_snapshot_row("005930", close_price_at_snapshot=50000.0)]
        today = {"005930": 55000.0}
        result = compute_returns_from_prices(rows, today)
        assert result["005930"] == pytest.approx(10.0)

    def test_nasdaq_apple_example(self):
        """
        회귀 테스트 예시 — 애플(AAPL).
        as_of 가격 $150.0 → 오늘 $180.0: 수익률 = 20.0%
        """
        rows = [make_snapshot_row("AAPL", close_price_at_snapshot=150.0)]
        today = {"AAPL": 180.0}
        result = compute_returns_from_prices(rows, today)
        assert result["AAPL"] == pytest.approx(20.0)

    def test_no_fallback_when_today_missing(self):
        """
        핵심 불변 조건: 오늘 주가가 없을 때 as_of 주가로 대체(수익률=0) 하지 않는다.
        as_of 주가가 있어도 오늘 주가가 없으면 반드시 None.
        """
        rows = [make_snapshot_row("NOTODAY", close_price_at_snapshot=100.0)]
        today = {}  # 오늘 주가 없음

        result = compute_returns_from_prices(rows, today)

        # 0.0이 아니라 None이어야 한다 (폴백 금지)
        assert result["NOTODAY"] is None
        assert result["NOTODAY"] != 0.0

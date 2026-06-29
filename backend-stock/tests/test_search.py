"""
검색·시세 기능 단위 테스트.

compute_quote_metrics: 손 검산값과 대조 (DB 불필요, 순수 계산 로직).
검색 필터 로직: ILIKE 동작을 파이썬으로 시뮬레이션해 부분일치·접두·동명 케이스 검증.
"""

import numpy as np
import pandas as pd
import pytest

from fomobot.services.calculator import PERIOD_TO_DAYS, compute_quote_metrics


# ── compute_quote_metrics 손 검산 ─────────────────────────────────────────────

def _make_series(prices: list[float], start: str = "2024-01-02") -> pd.Series:
    idx = pd.date_range(start, periods=len(prices), freq="B")
    return pd.Series(prices, index=idx)


class TestComputeQuoteMetrics:
    def test_삼성전자_7거래일_수익률_손검산(self):
        """
        가상 삼성전자 7거래일 데이터.
        시작가 55000, 종료가 57200
        return_pct = (57200 / 55000 - 1) × 100 = 4.0%
        """
        prices = [55000, 55500, 56000, 55800, 56500, 57000, 57200]
        series = _make_series(prices)
        result = compute_quote_metrics(series)
        expected = (57200 / 55000 - 1) * 100
        assert result["return_pct"] == pytest.approx(expected, rel=1e-6)

    def test_손실_종목_수익률(self):
        """100 → 80: return_pct = -20.0%"""
        series = _make_series([100.0, 95.0, 90.0, 85.0, 80.0])
        result = compute_quote_metrics(series)
        assert result["return_pct"] == pytest.approx(-20.0)

    def test_mdd_손검산(self):
        """
        prices: 100 → 120 → 90 → 110
        고점=120, 저점(고점 이후)=90
        MDD = (90 - 120) / 120 × 100 = -25.0%
        """
        series = _make_series([100.0, 120.0, 90.0, 110.0])
        result = compute_quote_metrics(series)
        assert result["mdd_pct"] == pytest.approx(-25.0)

    def test_단조_상승_mdd_zero(self):
        """단조 상승 시 MDD = 0%."""
        series = _make_series([100.0, 105.0, 110.0, 115.0, 120.0])
        result = compute_quote_metrics(series)
        assert result["mdd_pct"] == pytest.approx(0.0, abs=1e-9)

    def test_volatility_손검산(self):
        """
        일간 수익률 std를 직접 계산해 연율화 변동성과 비교.
        prices: 100, 110, 99, 108.9, 98.01
        """
        prices = [100.0, 110.0, 99.0, 108.9, 98.01]
        series = _make_series(prices)
        result = compute_quote_metrics(series)

        daily = pd.Series(prices).pct_change().dropna()
        expected_vol = daily.std() * np.sqrt(252) * 100
        assert result["volatility_annualized_pct"] == pytest.approx(expected_vol, rel=1e-6)

    def test_단일_행_모든_지표_None(self):
        """데이터가 1개면 계산 불가 → 모두 None."""
        result = compute_quote_metrics(_make_series([100.0]))
        assert result["return_pct"] is None
        assert result["mdd_pct"] is None
        assert result["volatility_annualized_pct"] is None

    def test_빈_시리즈_모든_지표_None(self):
        result = compute_quote_metrics(pd.Series(dtype=float))
        assert result["return_pct"] is None
        assert result["mdd_pct"] is None
        assert result["volatility_annualized_pct"] is None

    def test_수익률_양수_mdd_음수_부호_확인(self):
        """수익률은 양수, MDD는 음수 또는 0 — 부호 일관성."""
        prices = [100.0, 130.0, 95.0, 140.0]
        series = _make_series(prices)
        result = compute_quote_metrics(series)
        assert result["return_pct"] > 0
        assert result["mdd_pct"] is not None and result["mdd_pct"] <= 0


# ── PERIOD_TO_DAYS 검증 ────────────────────────────────────────────────────────

class TestPeriodToDays:
    def test_고정_기간_6개_모두_존재(self):
        required = {"1d", "7d", "30d", "90d", "365d", "1825d"}
        assert required.issubset(PERIOD_TO_DAYS.keys())

    def test_1825d는_5년(self):
        assert PERIOD_TO_DAYS["1825d"] == 5 * 365

    def test_365d는_1년(self):
        assert PERIOD_TO_DAYS["365d"] == 365


# ── 검색 필터 로직 (DB 없이 Python 시뮬레이션) ────────────────────────────────

class TestSearchFilterLogic:
    """
    실제 DB ILIKE 동작을 파이썬으로 시뮬레이션.
    검색 우선순위: 정확 코드 → 코드 접두 → 이름 부분일치.
    """

    MASTER = [
        {"ticker": "005930", "name": "삼성전자"},
        {"ticker": "005935", "name": "삼성전자우"},
        {"ticker": "000660", "name": "SK하이닉스"},
        {"ticker": "035720", "name": "카카오"},
        {"ticker": "AAPL",   "name": "Apple Inc."},
        {"ticker": "MSFT",   "name": "Microsoft Corporation"},
    ]

    def _search(self, q: str) -> list[dict]:
        q_lower = q.lower()
        seen: set[str] = set()
        result: list[dict] = []

        def _add(item: dict) -> None:
            if item["ticker"] not in seen:
                result.append(item)
                seen.add(item["ticker"])

        # 1순위: 정확 코드 매칭
        for item in self.MASTER:
            if item["ticker"].lower() == q_lower:
                _add(item)
        # 2순위: 코드 접두 매칭
        for item in self.MASTER:
            if item["ticker"].lower().startswith(q_lower):
                _add(item)
        # 3순위: 이름 부분일치
        for item in self.MASTER:
            if q_lower in (item["name"] or "").lower():
                _add(item)

        return result

    def test_이름_부분일치_삼성(self):
        res = self._search("삼성")
        tickers = [r["ticker"] for r in res]
        assert "005930" in tickers
        assert "005935" in tickers
        assert "000660" not in tickers

    def test_동명_모두_반환(self):
        """'삼성전자' 검색 시 삼성전자 + 삼성전자우 둘 다 반환."""
        res = self._search("삼성전자")
        tickers = [r["ticker"] for r in res]
        assert "005930" in tickers
        assert "005935" in tickers

    def test_코드_접두_매칭(self):
        res = self._search("0059")
        tickers = [r["ticker"] for r in res]
        assert "005930" in tickers
        assert "005935" in tickers
        assert "000660" not in tickers

    def test_정확_코드_우선_정렬(self):
        """'005930' 입력 시 005930이 첫 번째 결과."""
        res = self._search("005930")
        assert res[0]["ticker"] == "005930"

    def test_대소문자_무시_영문_코드(self):
        res = self._search("aapl")
        tickers = [r["ticker"] for r in res]
        assert "AAPL" in tickers

    def test_대소문자_무시_영문_이름(self):
        res = self._search("microsoft")
        tickers = [r["ticker"] for r in res]
        assert "MSFT" in tickers

    def test_없는_검색어_빈_결과(self):
        res = self._search("ZZZZZ999")
        assert res == []

    def test_단일_종목_코드_정확_매칭(self):
        res = self._search("000660")
        assert len(res) == 1
        assert res[0]["ticker"] == "000660"

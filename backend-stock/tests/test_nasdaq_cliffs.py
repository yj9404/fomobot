"""NASDAQ 절벽 탐지 필터(워런트·초저가 제외)와 알림 요약 형식 테스트."""

from contextlib import nullcontext
from datetime import date

import pytest

from fomobot.batch import detect_nasdaq_quality as q
from fomobot.jobs.detect_nasdaq_cliffs import ALERT_DETAIL_LIMIT, format_candidates
from fomobot.services.nasdaq_listing import is_warrant_symbol


class TestIsWarrantSymbol:
    @pytest.mark.parametrize("ticker", ["KTTAW", "ASTSW", "VERIW"])
    def test_5자리_W는_워런트(self, ticker):
        assert is_warrant_symbol(ticker) is True

    @pytest.mark.parametrize("ticker", ["SNOW", "TWOW", "AAPL", "GOOGL", "MVIS"])
    def test_4자리_W나_일반_5자리는_정상(self, ticker):
        assert is_warrant_symbol(ticker) is False


def _cliff_row(ticker, c_before, c_after, cliff_date=date(2026, 9, 1), v_before=1000, v_at=100):
    """절벽 전후가 안정적인(안정-안정) 후보 행 한 건."""
    return {
        "ticker": ticker, "date": cliff_date, "c0": c_after, "v0": v_at,
        "cm5": c_before, "cm4": c_before, "cm3": c_before, "cm2": c_before, "cm1": c_before,
        "vm1": v_before,
        "cp1": c_after, "cp2": c_after, "cp3": c_after, "cp4": c_after, "cp5": c_after,
        "vp1": 100, "vp2": 100, "vp3": 100, "vp4": 100, "vp5": 100,
    }


@pytest.fixture
def run_detect(monkeypatch):
    def _run(rows):
        monkeypatch.setattr(q, "SyncSessionLocal", lambda: nullcontext())
        monkeypatch.setattr(q, "get_flagged_tickers_sync", lambda *a, **k: set())
        monkeypatch.setattr(q, "get_resolved_flags_sync", lambda *a, **k: {})
        monkeypatch.setattr(q, "get_cliff_candidates_sync", lambda *a, **k: rows)
        monkeypatch.setattr(q, "get_last_trading_day_sync", lambda *a, **k: date(2026, 10, 20))
        return q.detect_nasdaq_cliffs("nasdaq")
    return _run


class TestDetectFilters:
    def test_역분할형_절벽은_격리후보(self, run_detect):
        result = run_detect([_cliff_row("EHGO", 0.64, 2.87)])
        assert [c["ticker"] for c in result["isolate_candidates"]] == ["EHGO"]

    def test_워런트는_탐지에서_제외(self, run_detect):
        result = run_detect([_cliff_row("KTTAW", 0.64, 2.87)])
        assert result["isolate_candidates"] == [] and result["lag_possible"] == []

    def test_전후_모두_5센트_미만이면_반올림_노이즈로_제외(self, run_detect):
        result = run_detect([_cliff_row("TINY", 0.01, 0.003)])
        assert result["isolate_candidates"] == []

    def test_절벽_후_가격이_5센트_이상이면_유지(self, run_detect):
        # 0.04 → 0.20 (x5): 한쪽이라도 임계 이상이면 실제 점프일 수 있어 걸러내지 않는다
        result = run_detect([_cliff_row("JUMP", 0.04, 0.20)])
        assert [c["ticker"] for c in result["isolate_candidates"]] == ["JUMP"]


def _candidate(ticker, cliff_date, ratio, vol_ratio):
    return {"ticker": ticker, "isolate_cliffs": [
        {"cliff_date": cliff_date, "ratio": ratio, "vol_ratio": vol_ratio},
    ]}


class TestFormatCandidates:
    def test_최근_절벽_순으로_날짜_배율_거래량비_표기(self):
        text = format_candidates([
            _candidate("OLD", date(2026, 8, 14), 4.9, 0.1),
            _candidate("NEW", date(2026, 10, 14), 4.49, 0.12),
        ])
        assert text == "NEW 10-14 x4.49 vol0.1, OLD 08-14 x4.90 vol0.1"

    def test_종목당_가장_최근_절벽만_표기(self):
        cand = {"ticker": "OMH", "isolate_cliffs": [
            {"cliff_date": date(2026, 7, 21), "ratio": 3.22, "vol_ratio": 2226.3},
            {"cliff_date": date(2026, 8, 27), "ratio": 38.78, "vol_ratio": 0.0},
        ]}
        assert format_candidates([cand]) == "OMH 08-27 x38.78 vol0.0"

    def test_거래량_무한대(self):
        assert format_candidates([_candidate("X", date(2026, 9, 1), 5.0, float("inf"))]) == "X 09-01 x5.00 volinf"

    def test_상세_표기_개수_제한(self):
        cands = [_candidate(f"T{i:02d}", date(2026, 9, 1), 5.0, 0.1) for i in range(ALERT_DETAIL_LIMIT + 5)]
        assert format_candidates(cands).endswith("외 5종목")

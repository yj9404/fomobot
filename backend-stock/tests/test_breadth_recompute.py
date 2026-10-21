"""breadth 다중 날짜 재계산(cron이 수집 구간 전체를 다시 집계) 테스트 — DB 없이 검증."""

from contextlib import nullcontext
from datetime import date, timedelta
from unittest.mock import MagicMock

import pandas as pd
import pytest

from fomobot.batch import collect_nasdaq, compute_breadth

D1, D2, D3 = date(2026, 10, 14), date(2026, 10, 15), date(2026, 10, 16)


@pytest.fixture
def calls(monkeypatch):
    """compute_market_breadth 호출 인자를 기록하고 날짜별 결과를 돌려준다."""
    recorded: list[date | None] = []

    def fake(market, target_date=None):
        recorded.append(target_date)
        return {"market": market, "date": target_date or D3}

    monkeypatch.setattr(compute_breadth, "compute_market_breadth", fake)
    return recorded


class TestRecomputeMarketBreadth:
    def test_날짜를_오름차순_중복없이_재계산(self, calls):
        results = compute_breadth.recompute_market_breadth("nasdaq", [D3, D1, D2, D1])
        assert calls == [D1, D2, D3]
        assert [r["date"] for r in results] == [D1, D2, D3]

    def test_빈_목록이면_최신일만_계산(self, calls):
        compute_breadth.recompute_market_breadth("kospi", [])
        assert calls == [None]  # target_date=None → 최신 거래일 (기존 동작)

    def test_한_날짜_실패해도_나머지는_계산하고_끝에_예외(self, monkeypatch):
        done: list[date] = []

        def fake(market, target_date=None):
            if target_date == D2:
                raise RuntimeError("db hiccup")
            done.append(target_date)
            return {"date": target_date}

        monkeypatch.setattr(compute_breadth, "compute_market_breadth", fake)

        with pytest.raises(RuntimeError, match="2026-10-15"):
            compute_breadth.recompute_market_breadth("nasdaq", [D1, D2, D3])
        assert done == [D1, D3]


def test_since는_시작일_이후_거래일을_재계산(monkeypatch, calls):
    monkeypatch.setattr(compute_breadth, "SyncSessionLocal", lambda: nullcontext(MagicMock()))
    seen = {}

    def fake_days(session, market, start_date):
        seen.update(market=market, start=start_date)
        return [D2, D3]

    monkeypatch.setattr(compute_breadth, "get_trading_days_since_sync", fake_days)

    compute_breadth.recompute_market_breadth_since("nasdaq", D1)

    assert seen == {"market": "nasdaq", "start": D1}
    assert calls == [D2, D3]


def test_NASDAQ_수집은_재조회_시작일을_반환(monkeypatch):
    """breadth 재계산 시작일은 수집이 실제로 쓴 start_date여야 한다(today - 7일)."""
    monkeypatch.setattr(collect_nasdaq, "_fetch_nasdaq_name_map", lambda: {})
    monkeypatch.setattr(collect_nasdaq, "fetch_nasdaq_tickers", lambda: [])
    monkeypatch.setattr(collect_nasdaq, "_download_batch", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(collect_nasdaq, "SyncSessionLocal", lambda: nullcontext(MagicMock()))

    today = date(2026, 10, 21)
    assert collect_nasdaq.run_nasdaq_collection(today) == today - timedelta(days=7)

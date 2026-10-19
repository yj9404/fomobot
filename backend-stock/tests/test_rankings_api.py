"""GET /api/stock/rankings 응답의 close_price 필드 테스트. DB 세션을 override해 실제 DB에 붙지 않는다."""

from datetime import date

from fastapi.testclient import TestClient

from fomobot.db.session import get_async_session
from fomobot.main import app


async def _override_session():
    yield object()


class _Row:
    def __init__(self, rank, ticker, close):
        self.rank = rank
        self.ticker = ticker
        self.name = f"종목{rank}"
        self.return_pct = 10.0 - rank
        self.mdd_pct = -1.0
        self.volatility_annualized_pct = 20.0
        self.excess_return_pct = 1.0
        self.close_price_at_snapshot = close
        self.halt_resumption = False
        self.first_valid_date = None
        self.start_validity = None


def _get(monkeypatch, rows):
    async def _latest(session, market, period):
        return date(2026, 10, 16)

    async def _rows(*args, **kwargs):
        return rows

    monkeypatch.setattr("fomobot.api.rankings.get_latest_snapshot_date", _latest)
    monkeypatch.setattr("fomobot.api.rankings.get_rankings", _rows)
    app.dependency_overrides[get_async_session] = _override_session
    try:
        return TestClient(app).get(
            "/api/stock/rankings", params={"market": "nasdaq", "period": "30d"}
        )
    finally:
        app.dependency_overrides.pop(get_async_session, None)


def test_스냅샷에_저장된_종가를_close_price로_반환(monkeypatch):
    r = _get(monkeypatch, [_Row(1, "NVDA", 187.25)])
    assert r.status_code == 200
    assert r.json()["rankings"][0]["close_price"] == 187.25


def test_종가가_저장되지_않은_스냅샷은_null(monkeypatch):
    r = _get(monkeypatch, [_Row(1, "NVDA", None)])
    assert r.status_code == 200
    assert r.json()["rankings"][0]["close_price"] is None

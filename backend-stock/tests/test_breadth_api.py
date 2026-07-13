"""GET /api/breadth 엔드포인트 테스트. DB 세션을 override해 실제 DB에 붙지 않는다."""

from datetime import date

from fastapi.testclient import TestClient

from fomobot.db.session import get_async_session
from fomobot.main import app


class _FakeSession:
    pass


async def _override_session():
    yield _FakeSession()


class _FakeRow:
    market = "kospi"
    date = date(2026, 7, 10)
    advancers = 802
    decliners = 92
    unchanged = 51
    excluded = 0
    halted = 32
    total = 945


class TestBreadthEndpoint:
    def test_데이터_없으면_404(self, monkeypatch):
        async def _fake_none(session, market):
            return None

        monkeypatch.setattr("fomobot.api.breadth.get_latest_market_breadth_async", _fake_none)
        app.dependency_overrides[get_async_session] = _override_session
        try:
            client = TestClient(app)
            r = client.get("/api/breadth", params={"market": "kospi"})
            assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_데이터_있으면_200과_값을_그대로_반환(self, monkeypatch):
        async def _fake_row(session, market):
            return _FakeRow()

        monkeypatch.setattr("fomobot.api.breadth.get_latest_market_breadth_async", _fake_row)
        app.dependency_overrides[get_async_session] = _override_session
        try:
            client = TestClient(app)
            r = client.get("/api/breadth", params={"market": "kospi"})
            assert r.status_code == 200
            body = r.json()
            assert body["advancers"] == 802
            assert body["decliners"] == 92
            assert body["unchanged"] == 51
            assert body["date"] == "2026-07-10"
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_잘못된_market_값은_422(self):
        client = TestClient(app)
        r = client.get("/api/breadth", params={"market": "nyse"})
        assert r.status_code == 422

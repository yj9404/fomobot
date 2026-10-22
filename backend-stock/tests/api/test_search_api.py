"""GET /api/stock/search 엔드포인트 테스트."""

from fastapi.testclient import TestClient
import pytest

from fomobot.api.search import _get_session
from fomobot.main import app


class _FakeSession:
    pass


async def _override_session():
    yield _FakeSession()


class _FakeRow:
    def __init__(self, ticker, name, is_active):
        self.ticker = ticker
        self.name = name
        self.is_active = is_active


class TestSearchEndpoint:
    @pytest.fixture(autouse=True)
    def setup_session_override(self):
        app.dependency_overrides[_get_session] = _override_session
        yield
        app.dependency_overrides.pop(_get_session, None)

    def test_검색_성공(self, monkeypatch):
        async def _fake_search(session, market, q):
            return [
                _FakeRow(ticker="005930", name="삼성전자", is_active=True),
                _FakeRow(ticker="005935", name="삼성전자우", is_active=True)
            ]

        monkeypatch.setattr("fomobot.api.search.search_securities", _fake_search)
        client = TestClient(app)

        r = client.get("/api/stock/search", params={"market": "kospi", "q": "삼성"})
        assert r.status_code == 200
        body = r.json()
        assert body["market"] == "kospi"
        assert body["query"] == "삼성"
        assert len(body["results"]) == 2

        assert body["results"][0]["ticker"] == "005930"
        assert body["results"][0]["name"] == "삼성전자"
        assert body["results"][0]["is_active"] is True

        assert body["results"][1]["ticker"] == "005935"
        assert body["results"][1]["name"] == "삼성전자우"
        assert body["results"][1]["is_active"] is True

    def test_빈_검색결과(self, monkeypatch):
        async def _fake_empty_search(session, market, q):
            return []

        monkeypatch.setattr("fomobot.api.search.search_securities", _fake_empty_search)
        client = TestClient(app)

        r = client.get("/api/stock/search", params={"market": "kospi", "q": "없는종목"})
        assert r.status_code == 200
        body = r.json()
        assert body["results"] == []

    def test_잘못된_market_값은_422(self):
        client = TestClient(app)
        r = client.get("/api/stock/search", params={"market": "invalid_market", "q": "삼성"})
        assert r.status_code == 422

    def test_검색어_길이_미달_422(self):
        client = TestClient(app)
        r = client.get("/api/stock/search", params={"market": "kospi", "q": ""})
        assert r.status_code == 422

    def test_검색어_길이_초과_422(self):
        client = TestClient(app)
        r = client.get("/api/stock/search", params={"market": "kospi", "q": "a" * 101})
        assert r.status_code == 422

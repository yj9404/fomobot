"""
종목 뉴스 API 테스트 — 웹(/api/stock/news/{ticker}, 3건 유지)과 토스(/api/stock/news/{ticker}/toss).
DB 조회 함수를 fake로 바꿔 실제 DB에 붙지 않는다.
"""

from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from fomobot.db.session import get_async_session
from fomobot.main import app
from fomobot.services.news_display import is_advice_title, press_name, safe_web_host


def row(title: str, link: str, day: int) -> SimpleNamespace:
    return SimpleNamespace(title=title, link=link, published_at=date(2026, 10, day))


# get_stock_news_async와 같이 발행일 최신순.
NEWS = {
    "005930": [
        row("삼성전자 주가 급등 마감", "https://www.hankyung.com/article/1", 27),
        row("삼성전자 목표주가 상향", "https://www.mk.co.kr/news/2", 27),
        row("삼성전자 외국인 순매수 1위", "https://www.edaily.co.kr/3", 26),
        row("삼성전자 신고가", "https://n.news.naver.com/mnews/article/001/4", 26),
        row("삼성전자 실적 발표", "javascript:alert(1)", 25),
        row("삼성전자 반도체 공장 증설", "http://m.unknownpress.kr/5", 25),
        row("삼성전자 상한가 근접", "https://biz.chosun.com/6", 24),
        row("삼성전자 노사 합의", "https://www.yna.co.kr/7", 24),
        row("삼성전자 배당 확대", "https://www.newsis.com/8", 23),
    ],
}


async def _fake_news(session, ticker, ttl_days):
    return NEWS.get(ticker, [])


async def _override_session():
    yield object()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("fomobot.api.news.get_stock_news_async", _fake_news)
    app.dependency_overrides[get_async_session] = _override_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_async_session, None)


class TestWebEndpoint:
    def test_keeps_three_articles_unfiltered(self, client):
        """배치가 5건 이상 저장해도 웹은 기존처럼 최신 3건을 필터 없이 그대로 준다."""
        r = client.get("/api/stock/news/005930")
        assert r.status_code == 200
        body = r.json()
        assert [a["link"] for a in body["articles"]] == [
            "https://www.hankyung.com/article/1",
            "https://www.mk.co.kr/news/2",
            "https://www.edaily.co.kr/3",
        ]
        assert set(body["articles"][0]) == {"title", "link", "published_at"}

    def test_empty(self, client):
        assert client.get("/api/stock/news/000000").json() == {"ticker": "000000", "articles": []}


class TestTossEndpoint:
    def test_filters_and_limits_to_five(self, client):
        r = client.get("/api/stock/news/005930/toss")
        assert r.status_code == 200
        articles = r.json()["articles"]
        # 목표주가·순매수 제목과 javascript: 링크는 빠지고, 남은 것 중 최신 5건.
        assert [(a["source"], a["url"]) for a in articles] == [
            ("한국경제", "https://www.hankyung.com/article/1"),
            ("네이버뉴스", "https://n.news.naver.com/mnews/article/001/4"),
            ("unknownpress.kr", "http://m.unknownpress.kr/5"),
            ("조선비즈", "https://biz.chosun.com/6"),
            ("연합뉴스", "https://www.yna.co.kr/7"),
        ]
        assert articles[0] == {
            "title": "삼성전자 주가 급등 마감",
            "source": "한국경제",
            "url": "https://www.hankyung.com/article/1",
            "published_at": "2026-10-27",
        }

    def test_empty(self, client):
        assert client.get("/api/stock/news/000000/toss").json() == {"ticker": "000000", "articles": []}


class TestNewsDisplay:
    @pytest.mark.parametrize("link", [
        "javascript:alert(1)", "intent://x#Intent;end", "supertoss://home", "ftp://a.com/x", "https://", "not a url",
    ])
    def test_rejects_non_web_links(self, link):
        assert safe_web_host(link) is None

    def test_accepts_web_links(self):
        assert safe_web_host("HTTPS://News.Naver.com/a") == "news.naver.com"
        assert safe_web_host("http://www.yna.co.kr/a") == "www.yna.co.kr"

    @pytest.mark.parametrize(("host", "name"), [
        ("n.news.naver.com", "네이버뉴스"),
        ("news.naver.com", "네이버뉴스"),
        ("m.mk.co.kr", "매일경제"),
        ("biz.chosun.com", "조선비즈"),
        ("www.chosun.com", "조선일보"),
        ("biz.sbs.co.kr", "SBS Biz"),
        ("www.newpress.com", "newpress.com"),
        ("blog.naver.com", "blog.naver.com"),
        ("notmk.co.kr", "notmk.co.kr"),
    ])
    def test_press_name(self, host, name):
        assert press_name(host) == name

    @pytest.mark.parametrize("title", [
        "삼성전자 매수 기회", "증권가 추천 종목", "목표가 상향", "목표주가 10만원", "유망주 3선",
        "지금 사야 할 종목", "바구니에 담아라", "리딩방 주의", "수익 보장", "수익보장",
    ])
    def test_advice_titles(self, title):
        assert is_advice_title(title)

    @pytest.mark.parametrize("title", ["삼성전자 급등", "SK하이닉스 상한가", "코스피 급락 마감", "실적 발표"])
    def test_price_movement_titles_kept(self, title):
        assert not is_advice_title(title)

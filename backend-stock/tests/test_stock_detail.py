"""종목 상세(/api/stock/detail)와 토스 공유 카드(/api/og/toss/*) 테스트. DB 조회 함수를 fake로 바꿔 실제 DB에 붙지 않는다."""

from datetime import date
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from fomobot.db.session import get_async_session
from fomobot.main import app
from fomobot.services.og_card_toss import fmt_price

# 시장 거래일 달력. 2026-10-03(토)·10-04(일)·10-05(월, 가상 휴장)은 없다.
TRADING_DAYS = {
    "kospi": [date(2021, 10, 1), date(2025, 10, 1), date(2026, 9, 15), date(2026, 9, 30),
              date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 6), date(2026, 10, 14),
              date(2026, 10, 15)],
    "nasdaq": [date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 14)],
}

SECURITIES = {
    ("kospi", "005930"): ("삼성전자", True),
    ("kospi", "111111"): ("신규상장", True),
    ("kospi", "222222"): ("거래정지", True),
    ("kospi", "999999"): ("정정중종목", True),
    ("kospi", "333333"): ("시세없음", False),
    ("nasdaq", "AAPL"): ("Apple Inc. Common Stock", True),
}

FLAGS = {("kospi", "999999"): "pending"}

SERIES = {
    ("kospi", "005930"): [
        (date(2021, 10, 1), 40_000.0),
        (date(2025, 10, 1), 50_000.0),
        (date(2026, 9, 15), 60_000.0),
        (date(2026, 10, 1), 70_000.0),
        (date(2026, 10, 14), 72_000.0),
        (date(2026, 10, 15), 75_600.0),
    ],
    # 2026-10-01 상장 — 30일 이상 구간은 상장일부터 계산된다.
    ("kospi", "111111"): [
        (date(2026, 10, 1), 10_000.0),
        (date(2026, 10, 6), 12_000.0),
        (date(2026, 10, 15), 15_000.0),
    ],
    # 2026-10-06 이후 거래정지 — 끝 거래일이 as_of보다 이르다.
    ("kospi", "222222"): [
        (date(2026, 9, 30), 5_000.0),
        (date(2026, 10, 2), 5_500.0),
        (date(2026, 10, 6), 4_000.0),
    ],
    ("kospi", "999999"): [
        (date(2026, 10, 1), 1_000.0),
        (date(2026, 10, 15), 50_000.0),
    ],
    ("nasdaq", "AAPL"): [
        (date(2026, 9, 30), 200.0),
        (date(2026, 10, 1), 180.0),
        (date(2026, 10, 14), 190.5),
    ],
}

SNAPSHOT_DATES = {("kospi", "30d"): [date(2026, 10, 14), date(2026, 10, 15)]}


class _FakeSecurity:
    def __init__(self, name, is_active):
        self.name = name
        self.is_active = is_active


async def _fake_security(session, market, ticker):
    row = SECURITIES.get((market, ticker))
    return None if row is None else _FakeSecurity(*row)


async def _fake_flag(session, market, ticker):
    return FLAGS.get((market, ticker))


async def _fake_last_trading_day(session, market, as_of=None):
    days = [d for d in TRADING_DAYS[market] if as_of is None or d <= as_of]
    return max(days) if days else None


async def _fake_series(session, market, ticker, start_date, end_date):
    return [r for r in SERIES.get((market, ticker), []) if start_date <= r[0] <= end_date]


async def _fake_nearest_snapshot(session, market, period, as_of):
    days = [d for d in SNAPSHOT_DATES.get((market, period), []) if d <= as_of]
    return max(days) if days else None


async def _override_session():
    yield object()


@pytest.fixture
def client(monkeypatch):
    mod = "fomobot.services.stock_detail"
    monkeypatch.setattr(f"{mod}.get_security_async", _fake_security)
    monkeypatch.setattr(f"{mod}.get_corporate_action_flag_status_async", _fake_flag)
    monkeypatch.setattr(f"{mod}.get_last_trading_day_async", _fake_last_trading_day)
    monkeypatch.setattr(f"{mod}.get_price_series_async", _fake_series)
    monkeypatch.setattr("fomobot.api.toss_og.get_nearest_snapshot_date", _fake_nearest_snapshot)
    app.dependency_overrides[get_async_session] = _override_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_async_session, None)


def _detail(client, market, ticker):
    return client.get("/api/stock/detail", params={"market": market, "ticker": ticker})


class TestStockDetail:
    def test_정상_종가와_기간별_등락률(self, client):
        r = _detail(client, "kospi", "005930")
        assert r.status_code == 200
        assert r.headers["cache-control"] == "public, max-age=300"
        body = r.json()
        assert body["status"] == "ok"
        assert body["name"] == "삼성전자"
        assert body["as_of"] == "2026-10-15"
        assert body["close"] == 75_600.0
        assert body["close_date"] == "2026-10-15"
        ch = body["changes"]
        # 전일: 10-14 → 10-15
        assert ch["1d"]["change_pct"] == pytest.approx(5.0)
        assert ch["1d"]["start_date"] == "2026-10-14"
        # 30일: 시작 09-15(거래일) → 60,000 → 75,600
        assert ch["30d"]["change_pct"] == pytest.approx(26.0)
        assert ch["30d"]["start_date"] == "2026-09-15"
        # 1년: 2025-10-15 이하 마지막 거래일 2025-10-01 → 50,000
        assert ch["365d"]["change_pct"] == pytest.approx(51.2)
        # 5년: 2021-10-16 이하 마지막 거래일 2021-10-01 → 40,000
        assert ch["1825d"]["change_pct"] == pytest.approx(89.0)
        assert ch["1825d"]["start_date"] == "2021-10-01"
        assert body["series"][0] == ["2021-10-01", 40_000.0]
        assert body["series"][-1] == ["2026-10-15", 75_600.0]

    def test_구간_시작일에_종목_데이터가_없으면_구간_안_첫_거래일부터(self, client):
        # 7일: 10-08 이하 마지막 시장 거래일 = 10-06. 이 종목은 10-06 행이 없어 10-14부터.
        ch = _detail(client, "kospi", "005930").json()["changes"]
        assert ch["7d"]["start_date"] == "2026-10-14"
        assert ch["7d"]["change_pct"] == pytest.approx(5.0)

    def test_상장이_늦으면_첫_거래일부터_계산하고_시작일을_알린다(self, client):
        ch = _detail(client, "kospi", "111111").json()["changes"]
        assert ch["30d"]["change_pct"] == pytest.approx(50.0)
        assert ch["30d"]["start_date"] == "2026-10-01"
        assert ch["1825d"]["start_date"] == "2026-10-01"

    def test_거래정지_종목은_시장_최신일_기준이고_정지_이후_구간은_null(self, client):
        body = _detail(client, "kospi", "222222").json()
        assert body["status"] == "ok"
        assert body["as_of"] == "2026-10-15"
        assert body["close_date"] == "2026-10-06"
        assert body["close"] == 4_000.0
        assert body["changes"]["1d"] is None
        assert body["changes"]["7d"] is None
        assert body["changes"]["30d"]["change_pct"] == pytest.approx(-20.0)
        assert body["changes"]["30d"]["end_date"] == "2026-10-06"

    def test_정정_중_종목은_수치_없이_correcting(self, client):
        body = _detail(client, "kospi", "999999").json()
        assert body["status"] == "correcting"
        assert body["close"] is None
        assert body["series"] == []
        assert all(v is None for v in body["changes"].values())

    def test_시세가_없으면_no_data(self, client):
        body = _detail(client, "kospi", "333333").json()
        assert body["status"] == "no_data"
        assert body["is_active"] is False
        assert body["series"] == []

    def test_소문자_티커는_대문자로(self, client):
        body = _detail(client, "nasdaq", "aapl").json()
        assert body["ticker"] == "AAPL"
        # 전일: 10-13 이하 마지막 시장 거래일이 10-01이라 10-01 → 10-14
        assert body["changes"]["1d"]["start_date"] == "2026-10-01"
        assert body["changes"]["1d"]["change_pct"] == pytest.approx(5.0 + 5.0 / 6)

    def test_존재하지_않는_종목은_404_no_store(self, client):
        r = _detail(client, "kospi", "000000")
        assert r.status_code == 404
        assert r.headers["cache-control"] == "no-store"


class TestTossStockCard:
    def _get(self, client, path, date_):
        params = {} if date_ is None else {"date": date_}
        return client.get(path, params=params)

    def test_png_1200x600_immutable(self, client):
        r = self._get(client, "/api/og/toss/stock/kospi/005930.png", "2026-10-15")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
        assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
        img = Image.open(BytesIO(r.content))
        assert img.size == (1200, 600)

    def test_카드_버전_파라미터는_내용에_영향이_없다(self, client):
        path = "/api/og/toss/stock/kospi/005930.png"
        base = client.get(path, params={"date": "2026-10-15"})
        versioned = client.get(path, params={"date": "2026-10-15", "v": "2"})
        assert versioned.status_code == 200
        assert versioned.content == base.content

    def test_차트_구간(self, client):
        path = "/api/og/toss/stock/kospi/005930.png"
        # chart가 생기기 전에 퍼진 URL(chart 없음)은 1년 카드와 같다.
        base = client.get(path, params={"date": "2026-10-15"})
        year = client.get(path, params={"date": "2026-10-15", "chart": "365d"})
        week = client.get(path, params={"date": "2026-10-15", "chart": "7d"})
        assert year.status_code == week.status_code == 200
        assert year.content == base.content
        assert week.content != year.content

    @pytest.mark.parametrize("chart", ["1d", "2d", ""])
    def test_잘못된_차트_구간은_400_no_store(self, client, chart):
        r = client.get("/api/og/toss/stock/kospi/005930.png", params={"date": "2026-10-15", "chart": chart})
        assert r.status_code == 400
        assert r.headers["cache-control"] == "no-store"

    def test_과거_기준일과_nasdaq_거래정지_종목도_렌더링(self, client):
        assert self._get(client, "/api/og/toss/stock/kospi/005930.png", "2026-10-01").status_code == 200
        assert self._get(client, "/api/og/toss/stock/nasdaq/AAPL.png", "2026-10-14").status_code == 200
        assert self._get(client, "/api/og/toss/stock/kospi/222222.png", "2026-10-15").status_code == 200

    @pytest.mark.parametrize(
        "path,date_,status",
        [
            ("/api/og/toss/stock/kospi/005930.png", None, 400),
            ("/api/og/toss/stock/kospi/005930.png", "20261015", 400),
            ("/api/og/toss/stock/kospi/005930.png", "2026-02-30", 400),
            # 최신 데이터일 이후
            ("/api/og/toss/stock/kospi/005930.png", "2026-10-16", 400),
            # 비거래일(토요일) — 스냅하지 않는다
            ("/api/og/toss/stock/kospi/005930.png", "2026-10-03", 404),
            ("/api/og/toss/stock/kosdaq/005930.png", "2026-10-15", 404),
            ("/api/og/toss/stock/kospi/000000.png", "2026-10-15", 404),
            ("/api/og/toss/stock/kospi/999999.png", "2026-10-15", 404),
            ("/api/og/toss/stock/kospi/333333.png", "2026-10-15", 404),
        ],
    )
    def test_실패는_png가_아니고_no_store(self, client, path, date_, status):
        r = self._get(client, path, date_)
        assert r.status_code == status
        assert r.headers["cache-control"] == "no-store"
        assert not r.headers["content-type"].startswith("image/")


class TestTossRankingsCard:
    PATH = "/api/og/toss/rankings/kospi.png"
    OK = {"period": "30d", "cap": "all", "order": "desc", "date": "2026-10-15"}

    def test_png_1200x600(self, client):
        r = client.get(self.PATH, params=self.OK)
        assert r.status_code == 200
        assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert Image.open(BytesIO(r.content)).size == (1200, 600)

    @pytest.mark.parametrize(
        "override,status",
        [
            ({"period": "2d"}, 400),
            ({"cap": "huge"}, 400),
            ({"order": "up"}, 400),
            ({"date": "2026/10/15"}, 400),
            # 스냅샷이 없는 날(10-13 이하 가장 가까운 스냅샷 없음 / 10-16은 10-15로 스냅되면 안 됨)
            ({"date": "2026-10-13"}, 404),
            ({"date": "2026-10-16"}, 404),
            ({"period": "7d"}, 404),
        ],
    )
    def test_실패는_no_store(self, client, override, status):
        r = client.get(self.PATH, params={**self.OK, **override})
        assert r.status_code == status
        assert r.headers["cache-control"] == "no-store"

    def test_카드_버전_파라미터는_내용에_영향이_없다(self, client):
        base = client.get(self.PATH, params=self.OK)
        versioned = client.get(self.PATH, params={**self.OK, "v": "2"})
        assert versioned.status_code == 200
        assert versioned.content == base.content

    def test_지원하지_않는_시장(self, client):
        r = client.get("/api/og/toss/rankings/kosdaq.png", params=self.OK)
        assert r.status_code == 404


class TestFmtPrice:
    def test_frontend_fmtPrice와_같은_표기(self):
        assert fmt_price(75_600.0, "kospi") == "75,600원"
        assert fmt_price(75_600.4, "kospi") == "75,600원"
        assert fmt_price(190.5, "nasdaq") == "$190.50"
        assert fmt_price(1234.567, "nasdaq") == "$1,234.57"

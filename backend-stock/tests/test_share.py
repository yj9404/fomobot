"""공유 카드 엔드포인트(/api/share, /api/og) 테스트. DB 조회 함수를 fake로 바꿔 실제 DB에 붙지 않는다."""

from datetime import date
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from fomobot.db.session import get_async_session
from fomobot.main import app
from fomobot.services.og_card import fmt_money, fmt_pct
from fomobot.services.share import CURRENCY, PRINCIPAL

LATEST = {"kospi": date(2026, 10, 15), "nasdaq": date(2026, 10, 14)}

SECURITIES = {
    ("kospi", "005930"): "삼성전자",
    ("nasdaq", "AAPL"): "Apple Inc. Common Stock",
    ("kospi", "999999"): "정정중종목",
}

FLAGS = {("kospi", "999999"): "excluded"}

# 거래일만 존재하는 시계열. 2026-10-03(토)·10-05(월, 가상 휴장) 등은 없다.
SERIES = {
    ("kospi", "005930"): [
        (date(2026, 10, 1), 50_000.0),
        (date(2026, 10, 2), 60_000.0),
        (date(2026, 10, 6), 45_000.0),
        (date(2026, 10, 15), 75_000.0),
    ],
    ("nasdaq", "AAPL"): [
        (date(2026, 9, 30), 200.0),
        (date(2026, 10, 1), 180.0),
        (date(2026, 10, 14), 190.0),
    ],
    ("kospi", "999999"): [
        (date(2026, 10, 1), 1_000.0),
        (date(2026, 10, 15), 50_000.0),
    ],
}


class _FakeSecurity:
    def __init__(self, name):
        self.name = name


async def _fake_security(session, market, ticker):
    name = SECURITIES.get((market, ticker))
    return None if name is None else _FakeSecurity(name)


async def _fake_flag(session, market, ticker):
    return FLAGS.get((market, ticker))


async def _fake_last_trading_day(session, market, as_of=None):
    return LATEST[market]


async def _fake_series(session, market, ticker, start_date, end_date):
    return [r for r in SERIES.get((market, ticker), []) if start_date <= r[0] <= end_date]


async def _override_session():
    yield object()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("fomobot.services.share.get_security_async", _fake_security)
    monkeypatch.setattr("fomobot.services.share.get_corporate_action_flag_status_async", _fake_flag)
    monkeypatch.setattr("fomobot.services.share.get_last_trading_day_async", _fake_last_trading_day)
    monkeypatch.setattr("fomobot.services.share.get_price_series_async", _fake_series)
    app.dependency_overrides[get_async_session] = _override_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_async_session, None)


IMMUTABLE = "public, max-age=31536000, immutable"


class TestShareJson:
    def test_kospi_정상(self, client):
        r = client.get("/api/share/kospi/005930", params={"from": "2026-10-01", "to": "2026-10-15"})
        assert r.status_code == 200
        assert r.headers["cache-control"] == IMMUTABLE
        body = r.json()
        assert body["market"] == "kospi"
        assert body["ticker"] == "005930"
        assert body["name"] == "삼성전자"
        assert body["from"] == "2026-10-01"
        assert body["to"] == "2026-10-15"
        assert body["start_price"] == 50_000.0
        assert body["end_price"] == 75_000.0
        assert body["return_pct"] == pytest.approx(50.0)
        # 고점 60,000 → 저점 45,000
        assert body["mdd_pct"] == pytest.approx(-25.0)
        assert body["principal"] == 1_000_000
        assert body["end_value"] == 1_500_000
        assert body["currency"] == "KRW"

    def test_nasdaq_정상_달러_원금(self, client):
        r = client.get("/api/share/nasdaq/AAPL", params={"from": "2026-09-30", "to": "2026-10-14"})
        assert r.status_code == 200
        body = r.json()
        assert body["return_pct"] == pytest.approx(-5.0)
        assert body["mdd_pct"] == pytest.approx(-10.0)
        assert body["principal"] == 10_000
        assert body["end_value"] == 9_500
        assert body["currency"] == "USD"

    def test_소문자_티커는_대문자로_정규화(self, client):
        r = client.get("/api/share/nasdaq/aapl", params={"from": "2026-09-30", "to": "2026-10-14"})
        assert r.status_code == 200
        assert r.json()["ticker"] == "AAPL"

    def test_수치_파라미터는_무시된다(self, client):
        r = client.get(
            "/api/share/kospi/005930",
            params={"from": "2026-10-01", "to": "2026-10-15", "ret": "99999", "return_pct": "99999"},
        )
        assert r.status_code == 200
        assert r.json()["return_pct"] == pytest.approx(50.0)

    @pytest.mark.parametrize(
        "path,params,status",
        [
            # 존재하지 않는 티커
            ("/api/share/kospi/000000", {"from": "2026-10-01", "to": "2026-10-15"}, 404),
            # 잘못된 market
            ("/api/share/kosdaq/005930", {"from": "2026-10-01", "to": "2026-10-15"}, 404),
            # 비거래일 (from=토요일, to=가상 휴장일)
            ("/api/share/kospi/005930", {"from": "2026-10-03", "to": "2026-10-15"}, 404),
            ("/api/share/kospi/005930", {"from": "2026-10-01", "to": "2026-10-05"}, 404),
            # from >= to
            ("/api/share/kospi/005930", {"from": "2026-10-15", "to": "2026-10-01"}, 400),
            ("/api/share/kospi/005930", {"from": "2026-10-15", "to": "2026-10-15"}, 400),
            # 미래 날짜 (최신 데이터일 이후)
            ("/api/share/kospi/005930", {"from": "2026-10-01", "to": "2026-10-16"}, 400),
            # 날짜 형식 위반 / 누락
            ("/api/share/kospi/005930", {"from": "20261001", "to": "2026-10-15"}, 400),
            ("/api/share/kospi/005930", {"from": "2026-02-30", "to": "2026-10-15"}, 400),
            ("/api/share/kospi/005930", {"to": "2026-10-15"}, 400),
            # 정정 중(excluded) 종목
            ("/api/share/kospi/999999", {"from": "2026-10-01", "to": "2026-10-15"}, 404),
        ],
    )
    def test_실패_케이스는_no_store(self, client, path, params, status):
        r = client.get(path, params=params)
        assert r.status_code == status
        assert r.headers["cache-control"] == "no-store"


class TestErrorMessage:
    @pytest.mark.parametrize(
        "params,detail",
        [
            ({"from": "20261001", "to": "2026-10-15"}, "from은 YYYY-MM-DD 형식이어야 합니다."),
            ({"from": "2026-10-01", "to": "20261015"}, "to는 YYYY-MM-DD 형식이어야 합니다."),
            ({"from": "2026-02-30", "to": "2026-10-15"}, "from이 올바른 날짜가 아닙니다."),
            ({"from": "2026-10-01", "to": "2026-02-30"}, "to가 올바른 날짜가 아닙니다."),
        ],
    )
    def test_필드별_조사(self, client, params, detail):
        r = client.get("/api/share/kospi/005930", params=params)
        assert r.status_code == 400
        assert r.json()["detail"] == detail


class TestOgImage:
    def test_png_1200x630(self, client):
        r = client.get("/api/og/kospi/005930.png", params={"from": "2026-10-01", "to": "2026-10-15"})
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
        assert r.headers["cache-control"] == IMMUTABLE
        img = Image.open(BytesIO(r.content))
        assert img.format == "PNG"
        assert img.size == (1200, 630)

    def test_nasdaq_png(self, client):
        r = client.get("/api/og/nasdaq/AAPL.png", params={"from": "2026-09-30", "to": "2026-10-14"})
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"

    @pytest.mark.parametrize(
        "path,params,status",
        [
            ("/api/og/kospi/000000.png", {"from": "2026-10-01", "to": "2026-10-15"}, 404),
            ("/api/og/kospi/005930.png", {"from": "2026-10-03", "to": "2026-10-15"}, 404),
            ("/api/og/kospi/999999.png", {"from": "2026-10-01", "to": "2026-10-15"}, 404),
            ("/api/og/kospi/005930.png", {"from": "2026-10-01", "to": "2026-10-16"}, 400),
        ],
    )
    def test_실패는_png가_아니고_no_store(self, client, path, params, status):
        r = client.get(path, params=params)
        assert r.status_code == status
        assert r.headers["cache-control"] == "no-store"
        assert not r.headers["content-type"].startswith("image/")


class TestPrincipal:
    def test_원금은_kospi_100만원_nasdaq_1만달러로_고정(self):
        # 카드·랜딩·메타 문구가 모두 이 값을 전제로 한다. 바꾸면 R2 캐시 버전도 올려야 한다.
        assert PRINCIPAL == {"kospi": 1_000_000, "nasdaq": 10_000}
        assert CURRENCY == {"kospi": "KRW", "nasdaq": "USD"}


class TestFormat:
    def test_fmt_pct(self):
        assert fmt_pct(50.0) == "+50.0%"
        assert fmt_pct(-5.04) == "-5.0%"
        assert fmt_pct(1234.56) == "+1,234.6%"

    def test_fmt_pct_반올림_0은_부호_없음(self):
        assert fmt_pct(0.04) == "0.0%"
        assert fmt_pct(-0.04) == "0.0%"
        assert fmt_pct(0.0) == "0.0%"
        assert fmt_pct(0.05) == "+0.1%"

    def test_fmt_pct_반올림은_JS_toFixed와_같다(self):
        # 12.25·-12.25는 2진수로 정확히 표현되는 .x5 — Python 기본 포맷이면 12.2가 된다.
        assert fmt_pct(12.25) == "+12.3%"
        assert fmt_pct(-12.25) == "-12.3%"
        assert fmt_pct(0.25) == "+0.3%"

    def test_fmt_money(self):
        assert fmt_money(1_000_000, "KRW") == "₩1,000,000"
        assert fmt_money(1_033_000, "KRW") == "₩1,033,000"
        assert fmt_money(10_000, "USD") == "$10,000"
        assert fmt_money(9_500, "USD") == "$9,500"


class TestReturnFit:
    def test_긴_수익률은_글자_크기를_줄인다(self):
        from PIL import Image, ImageDraw

        from fomobot.services.og_card import CONTENT_WIDTH, FONT_RETURN, RETURN_SIZES, _fit_size

        draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        assert _fit_size(draw, "+12,345.6%", FONT_RETURN) is FONT_RETURN[RETURN_SIZES[0]]
        font = _fit_size(draw, "+1,234,567.8%", FONT_RETURN)
        assert font is not None and font is not FONT_RETURN[RETURN_SIZES[0]]
        assert draw.textlength("+1,234,567.8%", font=font) <= CONTENT_WIDTH

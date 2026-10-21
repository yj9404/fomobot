"""nasdaqlisted.txt 해석 규칙(when-issued 티커 제외·종목명 정리) 테스트."""

from unittest.mock import MagicMock

import pytest

from fomobot.batch import collect_nasdaq, compute_rankings
from fomobot.services.nasdaq_listing import is_when_issued_symbol, normalize_security_name

# 2026-10 실제 파일에서 가져온 행 형태 그대로 (WI 티커는 당시 DB에 남아 있던 것)
LISTING = "\n".join([
    "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares",
    "MMED|MiniMed Group, Inc. - Common Stock|Q|N|N|100|N|N",
    "MMEDV|MiniMed Group, Inc. - Common Stock When Issued|Q|N|N|100|N|N",
    "SKHYV|SK hynix Inc. - American Depository Shares|Q|N|N|100|N|N",
    "CRWV|CoreWeave, Inc. - Class A Common Stock|Q|N|N|100|N|N",
    "SNDK|Sandisk Corporation - Common Stock When-Issued|Q|N|N|40|N|N",
    "QQLV|Invesco QQQ Low Volatility ETF|G|N|N|100|Y|N",
    "File Creation Time: 1020202621:31|||||||",
])


@pytest.fixture
def mock_listing(monkeypatch):
    resp = MagicMock(text=LISTING)
    resp.raise_for_status.return_value = None
    get = MagicMock(return_value=resp)
    monkeypatch.setattr(collect_nasdaq.httpx, "get", get)
    return get


class TestIsWhenIssuedSymbol:
    @pytest.mark.parametrize("ticker", ["MFPVV", "MIDDV", "MMEDV", "SKHYV", "THRMV"])
    def test_5자리_V는_WI(self, ticker):
        assert is_when_issued_symbol(ticker) is True

    @pytest.mark.parametrize("ticker", ["CRWV", "FFIV", "VIAV", "MMED", "AAPL", "GOOGL"])
    def test_4자리_V나_일반_5자리는_정상(self, ticker):
        assert is_when_issued_symbol(ticker) is False


class TestNormalizeSecurityName:
    @pytest.mark.parametrize("raw, expected", [
        ("Sandisk Corporation - Common Stock When-Issued", "Sandisk Corporation - Common Stock"),
        ("MiniMed Group, Inc. - Common Stock When Issued", "MiniMed Group, Inc. - Common Stock"),
        (
            "The Middleby Corporation - Common Stock Ex-Distribution When Issued",
            "The Middleby Corporation - Common Stock",
        ),
        ("Foo Inc - Common Stock when-issued ", "Foo Inc - Common Stock"),
    ])
    def test_끝의_WI_표기_제거(self, raw, expected):
        assert normalize_security_name(raw) == expected

    def test_표기_없으면_그대로(self):
        assert normalize_security_name("Apple Inc. - Common Stock") == "Apple Inc. - Common Stock"

    def test_중간에_있는_단어는_건드리지_않음(self):
        name = "When Issued Holdings Corp - Common Stock"
        assert normalize_security_name(name) == name


class TestCollectNasdaqListing:
    def test_티커_목록에서_WI_제외(self, mock_listing):
        tickers = collect_nasdaq.fetch_nasdaq_tickers()
        assert tickers == ["MMED", "CRWV", "SNDK"]  # ETF·WI 제외, 4자리 V는 유지

    def test_제외된_WI_티커를_로그로_남김(self, mock_listing, caplog):
        with caplog.at_level("INFO", logger=collect_nasdaq.logger.name):
            collect_nasdaq.fetch_nasdaq_tickers()
        assert "MMEDV" in caplog.text and "SKHYV" in caplog.text

    def test_종목명_WI_표기_제거(self, mock_listing):
        name_map = collect_nasdaq._fetch_nasdaq_name_map()
        assert name_map["SNDK"] == "Sandisk Corporation - Common Stock"
        assert name_map["MMED"] == "MiniMed Group, Inc. - Common Stock"


def test_랭킹_종목명도_WI_표기_제거(monkeypatch):
    resp = MagicMock(text=LISTING)
    resp.raise_for_status.return_value = None
    monkeypatch.setattr("httpx.get", MagicMock(return_value=resp))

    name_map = compute_rankings._fetch_name_map("nasdaq", ["SNDK", "CRWV"])
    assert name_map == {
        "SNDK": "Sandisk Corporation - Common Stock",
        "CRWV": "CoreWeave, Inc. - Class A Common Stock",
    }

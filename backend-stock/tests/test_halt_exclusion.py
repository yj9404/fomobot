"""
find_long_halted_tickers 단위 테스트 — 장기 정지 판정은 랭킹 제외의 유일한 근거라
경계(9일/10일, 재개 직후, NULL 거래량)를 고정한다. DB 접근 없음.
"""

from datetime import date, timedelta

from fomobot.services.halt_resumption import HALT_MIN_TRADING_DAYS, find_long_halted_tickers


def _rows(ticker: str, volumes: list[int | None], end: date = date(2026, 10, 23)) -> list[dict]:
    """volumes를 날짜 오름차순(마지막이 end)으로 받아 행 목록을 만든다."""
    start = end - timedelta(days=len(volumes) - 1)
    return [
        {"ticker": ticker, "date": start + timedelta(days=i), "volume": v}
        for i, v in enumerate(volumes)
    ]


def test_최신부터_거래량0이_기준일수_연속이면_정지():
    rows = _rows("A", [100] + [0] * HALT_MIN_TRADING_DAYS)
    assert find_long_halted_tickers(rows) == {"A"}


def test_기준일수보다_하루_짧으면_정지_아님():
    rows = _rows("A", [100] + [0] * (HALT_MIN_TRADING_DAYS - 1))
    assert find_long_halted_tickers(rows) == set()


def test_재개되면_다음_판정부터_바로_제외_해제():
    """000880처럼 17거래일 정지 후 재개한 날 — 최신 행이 실거래면 정지가 아니다."""
    rows = _rows("A", [100] + [0] * 17 + [1_455_368])
    assert find_long_halted_tickers(rows) == set()


def test_NULL_거래량도_거래없음으로_센다():
    rows = _rows("A", [100] + [None] * HALT_MIN_TRADING_DAYS)
    assert find_long_halted_tickers(rows) == {"A"}


def test_입력_순서와_무관하게_최신일_기준으로_판정():
    rows = _rows("A", [100] + [0] * HALT_MIN_TRADING_DAYS)
    assert find_long_halted_tickers(list(reversed(rows))) == {"A"}


def test_여러_종목을_각각_판정():
    rows = (
        _rows("HALT", [0] * (HALT_MIN_TRADING_DAYS + 5))
        + _rows("LIVE", [10] * (HALT_MIN_TRADING_DAYS + 5))
        + _rows("SHORT", [10] * 5 + [0] * 3)
    )
    assert find_long_halted_tickers(rows) == {"HALT"}

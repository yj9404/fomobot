"""수집 구간 분할 감지(extract_splits)와 Sentry 알림(report_splits) 테스트."""

import sys
from contextlib import contextmanager
from datetime import date

import pandas as pd
import pytest

from fomobot.batch import collect_nasdaq

DAYS = pd.to_datetime(["2026-10-22", "2026-10-23", "2026-10-26"])


def _multi(**splits_by_ticker):
    """yfinance group_by='ticker' + actions=True 형태 (MultiIndex: ticker, field)."""
    cols = {}
    for t, splits in splits_by_ticker.items():
        cols[(t, "Close")] = [1.0, 1.0, 1.0]
        cols[(t, "Stock Splits")] = splits
    return pd.DataFrame(cols, index=DAYS)


class TestExtractSplits:
    def test_역분할과_정분할을_모두_읽음(self):
        df = _multi(GCTK=[0.0, 0.0, 0.5], AAPL=[0.0, 4.0, 0.0], MSFT=[0.0, 0.0, 0.0])
        found = collect_nasdaq.extract_splits(df, ["GCTK", "AAPL", "MSFT"])
        assert sorted((f["ticker"], f["date"], f["ratio"]) for f in found) == [
            ("AAPL", date(2026, 10, 23), 4.0),
            ("GCTK", date(2026, 10, 26), 0.5),
        ]

    def test_분할_없으면_빈_목록(self):
        assert collect_nasdaq.extract_splits(_multi(A=[0.0, 0.0, 0.0]), ["A"]) == []

    def test_NaN과_1배는_분할이_아님(self):
        df = _multi(A=[float("nan"), 1.0, 0.0])
        assert collect_nasdaq.extract_splits(df, ["A"]) == []

    def test_단일_티커_flat_컬럼(self):
        df = pd.DataFrame({"Close": [1.0, 1.0, 1.0], "Stock Splits": [0.0, 0.0, 0.2]}, index=DAYS)
        assert collect_nasdaq.extract_splits(df, ["EHGO"]) == [
            {"ticker": "EHGO", "date": date(2026, 10, 26), "ratio": 0.2},
        ]

    def test_actions_없이_받은_응답이나_빈_응답은_조용히_빈_목록(self):
        no_actions = pd.DataFrame({("A", "Close"): [1.0, 1.0, 1.0]}, index=DAYS)
        assert collect_nasdaq.extract_splits(no_actions, ["A"]) == []
        assert collect_nasdaq.extract_splits(pd.DataFrame(), ["A"]) == []

    def test_응답에_없는_티커는_건너뜀(self):
        assert collect_nasdaq.extract_splits(_multi(A=[0.0, 0.0, 0.5]), ["A", "MISSING"]) == [
            {"ticker": "A", "date": date(2026, 10, 26), "ratio": 0.5},
        ]

    def test_파싱_예외는_수집을_막지_않음(self):
        class Boom:
            @property
            def empty(self):
                raise RuntimeError("broken frame")

        assert collect_nasdaq.extract_splits(Boom(), ["A"]) == []


class TestReportSplits:
    @pytest.fixture
    def sentry(self, monkeypatch):
        """sentry_sdk를 대체해 capture된 (메시지, 레벨, fingerprint)를 모은다."""
        events, current = [], {}

        class Scope:
            fingerprint = None

        @contextmanager
        def new_scope():
            current["scope"] = Scope()
            yield current["scope"]

        def capture_message(message, level):
            events.append((message, level, current["scope"].fingerprint))

        fake = type("FakeSentry", (), {"new_scope": staticmethod(new_scope),
                                       "capture_message": staticmethod(capture_message)})
        monkeypatch.setitem(sys.modules, "sentry_sdk", fake)
        return events

    def test_분할마다_경고_하나와_고정_fingerprint(self, sentry):
        collect_nasdaq.report_splits([
            {"ticker": "GCTK", "date": date(2026, 10, 26), "ratio": 0.5},
            {"ticker": "AAPL", "date": date(2026, 10, 23), "ratio": 4.0},
        ])
        assert [(e[1], e[2]) for e in sentry] == [
            ("warning", ["nasdaq-split-detected", "GCTK", "2026-10-26"]),
            ("warning", ["nasdaq-split-detected", "AAPL", "2026-10-23"]),
        ]
        assert "역분할" in sentry[0][0] and "x2.00" in sentry[0][0]
        assert "정분할" in sentry[1][0]

    def test_분할_없으면_알리지_않음(self, sentry):
        collect_nasdaq.report_splits([])
        assert sentry == []

    def test_Sentry가_실패해도_예외를_내지_않음(self, monkeypatch):
        broken = type("Broken", (), {"new_scope": staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("x")))})
        monkeypatch.setitem(sys.modules, "sentry_sdk", broken)
        collect_nasdaq.report_splits([{"ticker": "A", "date": date(2026, 10, 26), "ratio": 0.5}])

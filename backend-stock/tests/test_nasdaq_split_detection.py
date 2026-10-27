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


TODAY = date(2026, 10, 26)


def _split(ticker, d, ratio):
    return {"ticker": ticker, "date": d, "ratio": ratio}


class TestReportSplits:
    @pytest.fixture
    def sentry(self, monkeypatch):
        """sentry_sdk를 대체해 capture된 이벤트와 scope 조작을 기록한다."""
        calls = {"events": [], "scopes": [], "flushed": 0}

        class Scope:
            fingerprint = None
            breadcrumbs_cleared = False

            def clear_breadcrumbs(self):
                self.breadcrumbs_cleared = True

        @contextmanager
        def isolation_scope():
            scope = Scope()
            calls["scopes"].append(scope)
            yield scope

        def capture_message(message, level):
            calls["events"].append((message, level, calls["scopes"][-1].fingerprint))
            return "evt-1"

        def flush(timeout=None):
            calls["flushed"] += 1

        fake = type("FakeSentry", (), {
            "isolation_scope": staticmethod(isolation_scope),
            "capture_message": staticmethod(capture_message),
            "flush": staticmethod(flush),
        })
        monkeypatch.setitem(sys.modules, "sentry_sdk", fake)
        return calls

    def test_최근_분할을_이벤트_한_건으로_요약(self, sentry):
        collect_nasdaq.report_splits([
            _split("GCTK", date(2026, 10, 26), 0.5),
            _split("AAPL", date(2026, 10, 24), 4.0),
        ], TODAY)
        (message, level, _), = sentry["events"]
        assert level == "warning"
        assert "2건(최근 2일)" in message
        assert "GCTK 10-26 역분할 0.5(x2.00)" in message and "AAPL 10-24 정분할 4(x0.25)" in message

    def test_오래된_분할은_이벤트에서_빠지고_로그에만_남음(self, sentry, caplog):
        with caplog.at_level("WARNING", logger=collect_nasdaq.logger.name):
            collect_nasdaq.report_splits([
                _split("GCTK", date(2026, 10, 26), 0.5),
                _split("OLD", date(2026, 10, 20), 0.1),
            ], TODAY)
        (message, _, _), = sentry["events"]
        assert "GCTK" in message and "OLD" not in message
        assert "OLD" in caplog.text  # 전체 목록은 로그에 있다

    def test_최근_분할이_없으면_이벤트를_보내지_않음(self, sentry):
        collect_nasdaq.report_splits([_split("OLD", date(2026, 10, 20), 0.1)], TODAY)
        collect_nasdaq.report_splits([], TODAY)
        assert sentry["events"] == []

    def test_breadcrumb를_비우고_flush하며_같은_집합은_같은_fingerprint(self, sentry):
        splits = [_split("GCTK", date(2026, 10, 26), 0.5), _split("EHGO", date(2026, 10, 25), 0.2)]
        collect_nasdaq.report_splits(splits, TODAY)
        collect_nasdaq.report_splits(list(reversed(splits)), TODAY)
        assert all(sc.breadcrumbs_cleared for sc in sentry["scopes"]) and sentry["flushed"] == 2
        (_, _, fp1), (_, _, fp2) = sentry["events"]
        assert fp1 == fp2 and fp1[0] == "nasdaq-split-detected"
        collect_nasdaq.report_splits(splits[:1], TODAY)
        assert sentry["events"][2][2] != fp1  # 집합이 다르면 새 이슈

    def test_상세_표기_개수_제한(self, sentry):
        many = [_split(f"T{i:02d}", date(2026, 10, 26), 0.5) for i in range(collect_nasdaq.SPLIT_ALERT_LIMIT + 4)]
        collect_nasdaq.report_splits(many, TODAY)
        assert sentry["events"][0][0].count("역분할") == collect_nasdaq.SPLIT_ALERT_LIMIT
        assert "외 4건" in sentry["events"][0][0]

    def test_Sentry_실패는_예외_없이_로그로_남김(self, monkeypatch, caplog):
        broken = type("Broken", (), {"isolation_scope": staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("x")))})
        monkeypatch.setitem(sys.modules, "sentry_sdk", broken)
        with caplog.at_level("WARNING", logger=collect_nasdaq.logger.name):
            collect_nasdaq.report_splits([_split("GCTK", date(2026, 10, 26), 0.5)], TODAY)
        assert "Sentry 전송 실패" in caplog.text

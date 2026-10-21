"""
jobs/collect.py의 breadth 실패 격리 테스트.

cron 서비스는 Railway Dashboard에서 Command만 오버라이드해 web 서비스와
별도 컨테이너로 실행되므로, web 서비스 배포 시 도는 `alembic upgrade head`를
거치지 않는다. 즉 web 재배포 전에 cron이 먼저 돌면 market_breadth_daily
테이블이 없는 상태로 breadth 계산이 호출될 수 있다 — 이 시나리오를
가정해 본 수집·랭킹 작업까지 실패하지 않는지 검증한다.
"""

import logging
from datetime import date

from fomobot.jobs import collect


def _raise_undefined_table(market, target_date=None):
    """market_breadth_daily 테이블이 아직 없는 상태를 흉내낸다."""
    raise Exception('relation "market_breadth_daily" does not exist')


class TestComputeBreadthIsolation:
    def test_테이블_없음_예외를_밖으로_전파하지_않는다(self, monkeypatch, caplog):
        monkeypatch.setattr(
            "fomobot.batch.compute_breadth.compute_market_breadth",
            _raise_undefined_table,
        )

        with caplog.at_level(logging.ERROR):
            collect._compute_breadth("kospi", dates=[date(2026, 10, 20)])  # 예외 전파 시 실패

        assert any("breadth" in r.message for r in caplog.records)


class TestRunSurvivesBreadthFailure:
    def test_breadth_테이블_없어도_수집_랭킹은_정상_완료된다(self, monkeypatch):
        calls: list[str] = []

        monkeypatch.setattr(collect, "_collect_kospi", lambda: calls.append("collect") or [])
        monkeypatch.setattr(
            collect, "_compute_rankings", lambda market: calls.append("rankings") or 10
        )
        monkeypatch.setattr(
            "fomobot.batch.compute_breadth.compute_market_breadth",
            _raise_undefined_table,
        )

        collect.run("kospi")  # SystemExit이 발생하면 이 줄에서 테스트 실패

        assert calls == ["collect", "rankings"]


class TestBreadthTargetsFromCollection:
    """수집이 이번 실행에서 건드린 날짜가 그대로 breadth 재계산 대상으로 넘어가는지."""

    def _stub_side_jobs(self, monkeypatch):
        monkeypatch.setattr(collect, "_compute_rankings", lambda market: 10)
        monkeypatch.setattr(collect, "_run_corporate_action_checks", lambda market: None)
        monkeypatch.setattr(collect, "_run_negative_price_guard", lambda market: None)

    def test_KOSPI는_수집한_거래일_목록으로_재계산(self, monkeypatch):
        self._stub_side_jobs(monkeypatch)
        days = [date(2026, 10, 15), date(2026, 10, 16)]
        monkeypatch.setattr(collect, "_collect_kospi", lambda: days)
        got = {}
        monkeypatch.setattr(
            "fomobot.batch.compute_breadth.recompute_market_breadth",
            lambda market, dates: got.update(market=market, dates=dates) or [],
        )

        collect.run("kospi")

        assert got == {"market": "kospi", "dates": days}

    def test_NASDAQ는_수집_재조회_시작일로_재계산(self, monkeypatch):
        self._stub_side_jobs(monkeypatch)
        start = date(2026, 10, 14)
        monkeypatch.setattr(collect, "_collect_nasdaq", lambda: start)
        got = {}
        monkeypatch.setattr(
            "fomobot.batch.compute_breadth.recompute_market_breadth_since",
            lambda market, start_date: got.update(market=market, start=start_date) or [],
        )

        collect.run("nasdaq")

        assert got == {"market": "nasdaq", "start": start}

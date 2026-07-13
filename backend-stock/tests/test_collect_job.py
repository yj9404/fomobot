"""
jobs/collect.py의 breadth 실패 격리 테스트.

cron 서비스는 Railway Dashboard에서 Command만 오버라이드해 web 서비스와
별도 컨테이너로 실행되므로, web 서비스 배포 시 도는 `alembic upgrade head`를
거치지 않는다. 즉 web 재배포 전에 cron이 먼저 돌면 market_breadth_daily
테이블이 없는 상태로 breadth 계산이 호출될 수 있다 — 이 시나리오를
가정해 본 수집·랭킹 작업까지 실패하지 않는지 검증한다.
"""

import logging

from fomobot.jobs import collect


def _raise_undefined_table(market):
    """market_breadth_daily 테이블이 아직 없는 상태를 흉내낸다."""
    raise Exception('relation "market_breadth_daily" does not exist')


class TestComputeBreadthIsolation:
    def test_테이블_없음_예외를_밖으로_전파하지_않는다(self, monkeypatch, caplog):
        monkeypatch.setattr(
            "fomobot.batch.compute_breadth.compute_market_breadth",
            _raise_undefined_table,
        )

        with caplog.at_level(logging.ERROR):
            collect._compute_breadth("kospi")  # 예외가 전파되면 이 줄에서 테스트 실패

        assert any("breadth" in r.message for r in caplog.records)


class TestRunSurvivesBreadthFailure:
    def test_breadth_테이블_없어도_수집_랭킹은_정상_완료된다(self, monkeypatch):
        calls: list[str] = []

        monkeypatch.setattr(collect, "_collect_kospi", lambda: calls.append("collect") or 0)
        monkeypatch.setattr(
            collect, "_compute_rankings", lambda market: calls.append("rankings") or 10
        )
        monkeypatch.setattr(
            "fomobot.batch.compute_breadth.compute_market_breadth",
            _raise_undefined_table,
        )

        collect.run("kospi")  # SystemExit이 발생하면 이 줄에서 테스트 실패

        assert calls == ["collect", "rankings"]

"""
compute_rankings_for_market의 periods 파라미터 회귀 테스트.

정기 cron·수동 backfill·gap-fill 세 곳이 이 함수를 공유하므로,
periods=None일 때 기존 동작(PERIOD_TO_DAYS 6개 전부 계산)이 깨지면
정기 배치가 조용히 망가진다. DB는 실제로 건드리지 않고 DB 접근 지점을
모두 monkeypatch해 순수 로직만 검증한다.
"""

from datetime import date

import pandas as pd
import pytest

from fomobot.batch import compute_rankings
from fomobot.services.calculator import PERIOD_TO_DAYS


class _FakeSessionCM:
    """`with SyncSessionLocal() as session:` 를 대체하는 더미 컨텍스트 매니저."""

    def __enter__(self):
        return None

    def __exit__(self, *exc_info):
        return False


def _fake_price_matrix(*_args, **_kwargs) -> tuple[pd.DataFrame, pd.DataFrame]:
    """2종목 × 2거래일짜리 최소 price_matrix. meta_df는 빈 DF로 필터 단계를 건너뛴다."""
    idx = pd.to_datetime(["2026-07-02", "2026-07-03"])
    price_matrix = pd.DataFrame(
        {"AAA": [100.0, 110.0], "BBB": [200.0, 190.0]}, index=idx
    )
    return price_matrix, pd.DataFrame()


@pytest.fixture
def captured_upserts(monkeypatch):
    """upsert_ranking_snapshots_sync를 가로채 실제 DB 대신 리스트에 기록."""
    captured: list[dict] = []

    def _fake_upsert(_session, records):
        captured.extend(records)

    monkeypatch.setattr(compute_rankings, "SyncSessionLocal", lambda: _FakeSessionCM())
    monkeypatch.setattr(compute_rankings, "_load_price_matrix", _fake_price_matrix)
    monkeypatch.setattr(compute_rankings, "get_index_range_sync", lambda *a, **k: [])
    monkeypatch.setattr(compute_rankings, "upsert_ranking_snapshots_sync", _fake_upsert)
    monkeypatch.setattr(compute_rankings, "_fetch_name_map", lambda *a, **k: {})
    return captured


class TestPeriodsParameterRegression:
    """periods=None ⇒ 기존과 완전히 동일하게 6개 기간 전부 계산되는지 고정."""

    def test_periods_none_계산되는_기간이_PERIOD_TO_DAYS_전체와_동일(
        self, captured_upserts
    ):
        compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 7, 3), periods=None, top=10
        )
        computed_periods = {r["period"] for r in captured_upserts}
        assert computed_periods == set(PERIOD_TO_DAYS.keys())

    def test_periods_생략시_기본값도_None과_동일(self, captured_upserts):
        """periods 인자 자체를 안 넘겨도(기본값) 6개 전부 계산 — 시그니처 기본값 보존."""
        compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 7, 3), top=10
        )
        computed_periods = {r["period"] for r in captured_upserts}
        assert computed_periods == set(PERIOD_TO_DAYS.keys())

    def test_periods_일부_지정시_그것만_계산(self, captured_upserts):
        """gap-fill처럼 특정 기간만 넘기면 그 기간만 계산 — 나머지는 손대지 않음."""
        compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 7, 3), periods=["1d", "7d"], top=10
        )
        computed_periods = {r["period"] for r in captured_upserts}
        assert computed_periods == {"1d", "7d"}

    def test_periods_빈_리스트면_아무것도_계산_안함(self, captured_upserts):
        count = compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 7, 3), periods=[], top=10
        )
        assert count == 0
        assert captured_upserts == []

    def test_periods_None일때_저장된_레코드_수가_기간별_지정_합계와_같다(
        self, captured_upserts, monkeypatch
    ):
        """전체 실행 결과가 기간별로 나눠 실행한 결과의 합집합과 동일한지 교차검증."""
        compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 7, 3), periods=None, top=10
        )
        full_run = list(captured_upserts)
        captured_upserts.clear()

        for period_key in PERIOD_TO_DAYS:
            compute_rankings.compute_rankings_for_market(
                "kospi", snapshot_date=date(2026, 7, 3), periods=[period_key], top=10
            )
        split_run = captured_upserts

        full_keys = sorted((r["period"], r["ticker"]) for r in full_run)
        split_keys = sorted((r["period"], r["ticker"]) for r in split_run)
        assert full_keys == split_keys

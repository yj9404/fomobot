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
    # start_date 거래일 스냅 조회 — 이 테스트들은 _load_price_matrix를 고정값으로
    # 대체했으므로 실제 스냅 여부와 무관, raw 값을 그대로 돌려줘 세션 접근만 피한다.
    monkeypatch.setattr(
        compute_rankings, "get_last_trading_day_sync", lambda _session, _market, as_of=None: as_of
    )
    return captured


class TestPeriodsParameterRegression:
    """periods=None ⇒ 기존과 완전히 동일하게 6개 기간 전부 계산되는지 고정."""

    def test_periods_none_계산되는_기간이_PERIOD_TO_DAYS_전체와_동일(
        self, captured_upserts
    ):
        compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 7, 3), periods=None
        )
        computed_periods = {r["period"] for r in captured_upserts}
        assert computed_periods == set(PERIOD_TO_DAYS.keys())

    def test_periods_생략시_기본값도_None과_동일(self, captured_upserts):
        """periods 인자 자체를 안 넘겨도(기본값) 6개 전부 계산 — 시그니처 기본값 보존."""
        compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 7, 3)
        )
        computed_periods = {r["period"] for r in captured_upserts}
        assert computed_periods == set(PERIOD_TO_DAYS.keys())

    def test_periods_일부_지정시_그것만_계산(self, captured_upserts):
        """gap-fill처럼 특정 기간만 넘기면 그 기간만 계산 — 나머지는 손대지 않음."""
        compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 7, 3), periods=["1d", "7d"]
        )
        computed_periods = {r["period"] for r in captured_upserts}
        assert computed_periods == {"1d", "7d"}

    def test_periods_빈_리스트면_아무것도_계산_안함(self, captured_upserts):
        count = compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 7, 3), periods=[]
        )
        assert count == 0
        assert captured_upserts == []

    def test_periods_None일때_저장된_레코드_수가_기간별_지정_합계와_같다(
        self, captured_upserts, monkeypatch
    ):
        """전체 실행 결과가 기간별로 나눠 실행한 결과의 합집합과 동일한지 교차검증."""
        compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 7, 3), periods=None
        )
        full_run = list(captured_upserts)
        captured_upserts.clear()

        for period_key in PERIOD_TO_DAYS:
            compute_rankings.compute_rankings_for_market(
                "kospi", snapshot_date=date(2026, 7, 3), periods=[period_key]
            )
        split_run = captured_upserts

        full_keys = sorted((r["period"], r["ticker"]) for r in full_run)
        split_keys = sorted((r["period"], r["ticker"]) for r in split_run)
        assert full_keys == split_keys


class TestPeriodStartDateSnapsToTradingDay:
    """
    회귀 방지: 기간별 start_date가 캘린더 일수로 비거래일에 떨어지면
    (특히 snapshot_date가 월요일일 때 "1d"의 start_date가 일요일이 되는 경우)
    실제 거래일로 스냅되는지 확인한다.

    2026-07-04 gap-fill 운영 로그에서 kospi 06-29(월)/1d가 이 버그로 0건
    저장된 것이 실제로 확인됨 — start_date가 일요일(비거래일)로 떨어져
    거래일이 1개뿐이 되고 compute_returns가 빈 결과를 반환했다.
    """

    def test_snapshot_date가_월요일이면_1d의_start_date가_직전_거래일로_스냅(
        self, monkeypatch
    ):
        raw_sunday = date(2026, 6, 28)  # 캘린더 계산 그대로면 이 날짜가 됨(비거래일)
        snapped_friday = date(2026, 6, 26)  # 실제 직전 거래일
        calls: list[tuple] = []

        def _fake_get_last_trading_day_sync(_session, _market, as_of=None):
            assert as_of == raw_sunday
            return snapped_friday

        def _fake_load_price_matrix(_session, _market, start_date, end_date):
            calls.append((start_date, end_date))
            idx = pd.to_datetime([start_date, end_date])
            return pd.DataFrame({"AAA": [100.0, 105.0]}, index=idx), pd.DataFrame()

        monkeypatch.setattr(compute_rankings, "SyncSessionLocal", lambda: _FakeSessionCM())
        monkeypatch.setattr(
            compute_rankings, "get_last_trading_day_sync", _fake_get_last_trading_day_sync
        )
        monkeypatch.setattr(compute_rankings, "_load_price_matrix", _fake_load_price_matrix)
        monkeypatch.setattr(compute_rankings, "get_index_range_sync", lambda *a, **k: [])
        monkeypatch.setattr(compute_rankings, "upsert_ranking_snapshots_sync", lambda *a, **k: None)
        monkeypatch.setattr(compute_rankings, "_fetch_name_map", lambda *a, **k: {})

        compute_rankings.compute_rankings_for_market(
            "kospi", snapshot_date=date(2026, 6, 29), periods=["1d"]
        )

        # _load_price_matrix가 일요일(raw_sunday)이 아니라 스냅된 금요일로 호출됐는지
        assert calls == [(snapped_friday, date(2026, 6, 29))]

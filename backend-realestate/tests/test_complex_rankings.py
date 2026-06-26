"""
단지 랭킹 계산 로직 테스트.

DB 없이 순수 Python 함수만 테스트한다.
손 검산 케이스: 래미안개포1단지 1년 기간 예시.
"""

from decimal import Decimal

import pandas as pd
from realestate.batch.complex_rankings import (
    _compute_window_stats,
    _determine_status,
    _get_windows,
    add_months,
    subtract_months,
)


# ── 날짜 헬퍼 ──────────────────────────────────────────────────────────

class TestSubtractMonths:
    def test_basic(self):
        assert subtract_months("202601", 3) == "202510"
        assert subtract_months("202601", 12) == "202501"
        assert subtract_months("202601", 24) == "202401"

    def test_year_boundary(self):
        assert subtract_months("202601", 1) == "202512"
        assert subtract_months("202603", 3) == "202512"

    def test_long_period(self):
        assert subtract_months("202601", 240) == "200601"


class TestAddMonths:
    def test_basic(self):
        assert add_months("202510", 3) == "202601"
        assert add_months("202501", 12) == "202601"

    def test_year_boundary(self):
        assert add_months("202512", 1) == "202601"
        assert add_months("202510", 5) == "202603"


# ── 윈도우 계산 ────────────────────────────────────────────────────────

class TestGetWindows:
    """N=3 기준 (기본값)."""

    def test_6m_past_only_start(self):
        """6m 구간은 P(6) ≤ 2N(6)이므로 과거 방향만 시작 앵커를 사용한다.
        따라서 종료 앵커와 겹치지 않는다."""
        snap = "202601"
        start_ym = subtract_months(snap, 6)  # "202507"
        sw, ew, overlap = _get_windows("6m", start_ym, snap, n=3)
        # 과거 방향만: [start-3, start] = [202504, 202507]
        assert sw == ("202504", "202507")
        # 종료 앵커: [end-3, end] = [202510, 202601]
        assert ew == ("202510", "202601")
        # 202507 < 202510 → 겹침 없음
        assert not overlap

    def test_3m_past_only_start(self):
        """3m 구간은 시작 앵커가 과거 방향만이다.
        start_w[1] == end_w[0] → 경계 1개월 겹침."""
        snap = "202601"
        start_ym = subtract_months(snap, 3)  # "202510"
        sw, ew, overlap = _get_windows("3m", start_ym, snap, n=3)
        # 시작 앵커: [start-3, start] = [202507, 202510]
        assert sw == ("202507", "202510")
        # 종료 앵커: [end-3, end] = [202510, 202601]
        assert ew == ("202510", "202601")
        # start_w[1] == end_w[0] = 202510 → 1개월 겹침
        assert overlap

    def test_1y_no_overlap(self):
        """1y 구간은 P(12) > 2N(6)이므로 대칭 창을 사용하고 겹침이 없다."""
        snap = "202601"
        start_ym = subtract_months(snap, 12)  # "202501"
        sw, ew, overlap = _get_windows("1y", start_ym, snap, n=3)
        assert sw == ("202410", "202504")
        assert ew == ("202510", "202601")
        assert not overlap

    def test_overlap_flag_only_for_3m(self):
        """1y 이상 구간 및 6m(과거 방향 적용)은 겹치지 않는다."""
        snap = "202601"
        for period, months in [("6m", 6), ("1y", 12), ("3y", 36)]:
            start_ym = subtract_months(snap, months)
            _, _, overlap = _get_windows(period, start_ym, snap, n=3)
            assert not overlap, f"{period} 구간에서 겹침이 발생해선 안됨"


# ── 윈도우 통계 계산 ───────────────────────────────────────────────────

class TestComputeWindowStats:
    def _make_df(self, rows: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(rows)
        df["price_per_sqm"] = df["price_per_sqm"].astype(float)
        return df

    def test_median_not_mean(self):
        """중위값은 평균이 아니다 (이상거래 방어)."""
        df = self._make_df([
            {"sigungu_code": "11680", "eupmyeondong": "개포동",
             "apt_name": "래미안개포1단지", "apt_name_norm": "래미안개포1단지",
             "complex_key": "KEY1", "deal_ym": "202501", "price_per_sqm": 40.0},
            {"sigungu_code": "11680", "eupmyeondong": "개포동",
             "apt_name": "래미안개포1단지", "apt_name_norm": "래미안개포1단지",
             "complex_key": "KEY1", "deal_ym": "202502", "price_per_sqm": 42.0},
            {"sigungu_code": "11680", "eupmyeondong": "개포동",
             "apt_name": "래미안개포1단지", "apt_name_norm": "래미안개포1단지",
             "complex_key": "KEY1", "deal_ym": "202503", "price_per_sqm": 200.0},  # 이상거래
        ])
        stats = _compute_window_stats(df)
        row = stats[stats["complex_key"] == "KEY1"].iloc[0]
        assert row["median_price"] == 42.0   # median(40, 42, 200) = 42
        assert row["tx_count"] == 3

    def test_empty_df(self):
        df = pd.DataFrame(columns=[
            "sigungu_code", "eupmyeondong", "apt_name", "apt_name_norm",
            "complex_key", "deal_ym", "price_per_sqm",
        ])
        stats = _compute_window_stats(df)
        assert stats.empty

    def test_multiple_complexes(self):
        """단지가 여럿이면 각각 별도 집계된다."""
        df = self._make_df([
            {"sigungu_code": "11680", "eupmyeondong": "개포동",
             "apt_name": "래미안개포1단지", "apt_name_norm": "래미안개포1단지",
             "complex_key": "KEY1", "deal_ym": "202501", "price_per_sqm": 50.0},
            {"sigungu_code": "11680", "eupmyeondong": "개포동",
             "apt_name": "개포주공", "apt_name_norm": "개포주공",
             "complex_key": "KEY2", "deal_ym": "202501", "price_per_sqm": 30.0},
        ])
        stats = _compute_window_stats(df)
        assert len(stats) == 2
        assert set(stats["complex_key"].tolist()) == {"KEY1", "KEY2"}


# ── 상태 결정 및 손 검산 ───────────────────────────────────────────────

class TestDetermineStatus:
    """
    손 검산 케이스: 래미안개포1단지 1년 기간.

    시작 윈도우 (202410~202504) 거래 4건:
        44.0, 46.0, 45.0, 47.0  → 중위값 = (45+46)/2 = 45.5 만원/㎡

    종료 윈도우 (202510~202601) 거래 4건:
        60.0, 62.0, 58.0, 61.0  → 중위값 = (60+61)/2 = 60.5 만원/㎡

    상승률 = (60.5 - 45.5) / 45.5 × 100 = 32.97...% → 반올림 32.97%
    """
    START_W = ("202410", "202504")
    END_W = ("202510", "202601")

    def test_hand_calculated_change_pct(self):
        status, reason, change = _determine_status(
            start_price=45.5,
            end_price=60.5,
            start_tx=4,
            end_tx=4,
            min_tx=3,
            start_w=self.START_W,
            end_w=self.END_W,
        )
        assert status == "ok"
        assert reason is None
        expected = Decimal("32.97")
        assert change == expected, f"기대값 {expected}, 실제 {change}"

    def test_ok_status(self):
        status, reason, change = _determine_status(
            start_price=40.0, end_price=60.0,
            start_tx=5, end_tx=5, min_tx=3,
            start_w=self.START_W, end_w=self.END_W,
        )
        assert status == "ok"
        assert change == Decimal("50.00")

    def test_no_start(self):
        """시작 데이터 없으면 no_start."""
        status, _, change = _determine_status(
            start_price=None, end_price=60.0,
            start_tx=None, end_tx=5, min_tx=3,
            start_w=self.START_W, end_w=self.END_W,
        )
        assert status == "no_start"
        assert change is None

    def test_no_end(self):
        """종료 데이터 없으면 no_end."""
        status, _, change = _determine_status(
            start_price=40.0, end_price=None,
            start_tx=5, end_tx=None, min_tx=3,
            start_w=self.START_W, end_w=self.END_W,
        )
        assert status == "no_end"
        assert change is None

    def test_insufficient_start_only(self):
        """시작 건수가 M 미만이면 제외 (종료가 충분해도)."""
        status, reason, change = _determine_status(
            start_price=40.0, end_price=60.0,
            start_tx=2, end_tx=5, min_tx=3,   # 시작 2건 < M=3
            start_w=self.START_W, end_w=self.END_W,
        )
        assert status == "insufficient"
        assert change is None
        assert "시작 윈도우 거래 2건" in reason

    def test_insufficient_end_only(self):
        """종료 건수가 M 미만이면 제외 (시작이 충분해도)."""
        status, reason, change = _determine_status(
            start_price=40.0, end_price=60.0,
            start_tx=5, end_tx=1, min_tx=3,   # 종료 1건 < M=3
            start_w=self.START_W, end_w=self.END_W,
        )
        assert status == "insufficient"
        assert change is None
        assert "종료 윈도우 거래 1건" in reason

    def test_both_exactly_m_passes(self):
        """시작·종료 양쪽 모두 정확히 M건이면 랭킹 포함."""
        status, _, change = _determine_status(
            start_price=40.0, end_price=50.0,
            start_tx=3, end_tx=3, min_tx=3,
            start_w=self.START_W, end_w=self.END_W,
        )
        assert status == "ok"
        assert change is not None

    def test_m_minus_one_excluded(self):
        """M-1 건이면 excluded."""
        status, _, _ = _determine_status(
            start_price=40.0, end_price=50.0,
            start_tx=2, end_tx=2, min_tx=3,
            start_w=self.START_W, end_w=self.END_W,
        )
        assert status == "insufficient"

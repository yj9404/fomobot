"""
gap-fill self-healing 로직 테스트.

find_gaps / plan_fill_jobs는 순수 함수라 DB 없이 검증 가능.
run_gap_fill_for_market은 DB 접근 지점을 monkeypatch해 오케스트레이션만 검증한다
(실제 DB에는 절대 쓰지 않는다).
"""

from datetime import date


from fomobot.batch import gap_fill
from fomobot.batch.gap_fill import GapScanResult, find_gaps, plan_fill_jobs


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _days(*strs: str) -> list[date]:
    return [_d(s) for s in strs]


class TestFindGapsIsolatedGap:
    def test_고립_단일일_gap은_fillable(self):
        """앞뒤 거래일 모두 존재하는데 가운데 하루만 빔 — 2026-07-03 인시던트와 동일 패턴."""
        trading_days = _days("2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06")
        existing = {_d("2026-07-01"), _d("2026-07-02"), _d("2026-07-06")}
        result = find_gaps(trading_days, existing)
        assert result.fillable == [_d("2026-07-03")]
        assert result.continuous_gaps == []

    def test_맨_앞_거래일이_비어도_fillable_아님(self):
        """이웃 앵커(이전 거래일)가 없어 고립 판정 불가."""
        trading_days = _days("2026-07-01", "2026-07-02", "2026-07-03")
        existing = {_d("2026-07-02"), _d("2026-07-03")}
        result = find_gaps(trading_days, existing)
        assert result.fillable == []

    def test_맨_뒤_거래일이_비어도_fillable_아님(self):
        """맨 뒤는 정기 cron이 책임지는 당일치 — gap-fill 대상 아님."""
        trading_days = _days("2026-07-01", "2026-07-02", "2026-07-03")
        existing = {_d("2026-07-01"), _d("2026-07-02")}
        result = find_gaps(trading_days, existing)
        assert result.fillable == []

    def test_모두_존재하면_gap_없음(self):
        trading_days = _days("2026-07-01", "2026-07-02", "2026-07-03")
        existing = set(trading_days)
        result = find_gaps(trading_days, existing)
        assert result.fillable == []
        assert result.continuous_gaps == []


class TestFindGapsContinuousGap:
    def test_연속_2거래일_공백은_fillable_아니고_continuous_gap(self):
        trading_days = _days(
            "2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03"
        )
        existing = {_d("2026-06-29"), _d("2026-07-02"), _d("2026-07-03")}
        result = find_gaps(trading_days, existing)
        assert result.fillable == []
        assert result.continuous_gaps == [(_d("2026-06-30"), _d("2026-07-01"))]

    def test_레거시_주간백필_구간은_하나의_날짜범위로_묶여_보고(self):
        """06-19~06-24처럼 여러 날이 통째로 비어도 개별 경고가 아니라 범위 1건."""
        trading_days = _days(
            "2026-06-18", "2026-06-19", "2026-06-22", "2026-06-23",
            "2026-06-24", "2026-06-25",
        )
        existing = {_d("2026-06-18"), _d("2026-06-25")}
        result = find_gaps(trading_days, existing)
        assert result.fillable == []
        assert result.continuous_gaps == [(_d("2026-06-19"), _d("2026-06-24"))]

    def test_진행중인_공백_1일은_고립도_연속도_아님(self):
        """가장 최근 거래일이 비어있는 상태 — 다음 거래일이 나와야 분류가 확정됨."""
        trading_days = _days("2026-07-01", "2026-07-02", "2026-07-03")
        existing = {_d("2026-07-01"), _d("2026-07-02")}
        result = find_gaps(trading_days, existing)
        assert result.fillable == []
        assert result.continuous_gaps == []  # 아직 "연속"으로 확정 안 됨 (길이 1, 경계)


class TestFindGapsRealIncidentReplay:
    def test_07_06_정기분_반영_후_07_03_고립_gap으로_전환(self):
        """
        07-03 인시던트: 다음 거래일(07-06, 월)이 들어오기 전엔 못 잡히고,
        정기 cron이 07-06을 채운 '다음 순간'부터 07-03이 고립 gap으로 전환된다.
        """
        trading_days = _days(
            "2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"
        )
        # 07-06 이전: 07-03이 마지막 거래일이라 fillable 아님
        existing_before = {_d("2026-06-30"), _d("2026-07-01"), _d("2026-07-02")}
        before = find_gaps(trading_days[:-1], existing_before)
        assert before.fillable == []

        # 07-06 정기분이 들어온 뒤: 07-03이 이웃(07-02, 07-06) 모두 존재 → fillable
        existing_after = existing_before | {_d("2026-07-06")}
        after = find_gaps(trading_days, existing_after)
        assert after.fillable == [_d("2026-07-03")]


class TestPlanFillJobs:
    def test_cap_이하면_전부_채택(self):
        scan = {
            "1d": GapScanResult(fillable=[_d("2026-07-03")]),
            "7d": GapScanResult(fillable=[_d("2026-07-03")]),
        }
        jobs, deferred = plan_fill_jobs(scan, cap=30)
        assert jobs == {_d("2026-07-03"): ["1d", "7d"]}
        assert deferred == 0

    def test_cap_초과시_오래된_날짜부터_채택_나머지는_이월(self):
        scan = {
            p: GapScanResult(fillable=[_d("2026-06-20"), _d("2026-06-25"), _d("2026-06-30")])
            for p in ["1d", "7d", "30d"]
        }
        jobs, deferred = plan_fill_jobs(scan, cap=5)
        total_accepted = sum(len(v) for v in jobs.values())
        assert total_accepted == 5
        assert deferred == 9 - 5
        # 가장 오래된 날짜(06-20)는 반드시 포함되어야 함
        assert _d("2026-06-20") in jobs

    def test_fillable_없으면_빈_계획(self):
        scan = {"1d": GapScanResult(), "7d": GapScanResult()}
        jobs, deferred = plan_fill_jobs(scan, cap=30)
        assert jobs == {}
        assert deferred == 0


class TestRunGapFillDryRun:
    def test_dry_run은_compute_rankings_호출_안함(self, monkeypatch):
        called = []

        def _fake_scan_market(market, lookback=10):
            return {
                "1d": GapScanResult(fillable=[_d("2026-07-03")]),
                "7d": GapScanResult(continuous_gaps=[(_d("2026-06-19"), _d("2026-06-24"))]),
            }

        def _fake_compute(*args, **kwargs):
            called.append((args, kwargs))
            return 100

        monkeypatch.setattr(gap_fill, "scan_market", _fake_scan_market)
        monkeypatch.setattr(gap_fill, "compute_rankings_for_market", _fake_compute)

        report = gap_fill.run_gap_fill_for_market("kospi", dry_run=True)

        assert called == []  # DB 쓰기로 이어지는 호출이 전혀 없어야 함
        assert report["dates_to_fill"] == {_d("2026-07-03"): ["1d"]}
        assert report["continuous_gaps"]["7d"] == [(_d("2026-06-19"), _d("2026-06-24"))]

    def test_dry_run_아니면_compute_rankings_호출됨(self, monkeypatch):
        called = []

        def _fake_scan_market(market, lookback=10):
            return {"1d": GapScanResult(fillable=[_d("2026-07-03")])}

        def _fake_compute(market, snapshot_date=None, periods=None, top=100):
            called.append((market, snapshot_date, periods))
            return 100

        monkeypatch.setattr(gap_fill, "scan_market", _fake_scan_market)
        monkeypatch.setattr(gap_fill, "compute_rankings_for_market", _fake_compute)

        report = gap_fill.run_gap_fill_for_market("kospi", dry_run=False)

        assert called == [("kospi", _d("2026-07-03"), ["1d"])]
        assert report["filled_records"] == 100

"""
랭킹 계산 로직 단위 테스트.

subtract_months, 상승률 계산, 데이터 부족 판정 등을 DB 없이 테스트한다.
"""

import pytest
from decimal import Decimal

from realestate.batch.compute_rankings import subtract_months, PERIOD_MONTHS


# ── 년월 산술 ──────────────────────────────────────────────────────────

class TestSubtractMonths:
    def test_same_year(self):
        assert subtract_months("202406", 3) == "202403"

    def test_cross_year(self):
        assert subtract_months("202402", 3) == "202311"

    def test_cross_year_january(self):
        assert subtract_months("202401", 1) == "202312"

    def test_1y(self):
        assert subtract_months("202406", 12) == "202306"

    def test_3y(self):
        assert subtract_months("202406", 36) == "202106"

    def test_20y(self):
        assert subtract_months("202606", 240) == "200606"

    def test_multiple_year_boundary(self):
        # 2024-01에서 13개월을 빼면 2022-12
        assert subtract_months("202401", 13) == "202212"


# ── 기간 정의 일관성 ────────────────────────────────────────────────────

def test_period_months_keys():
    """모든 기간 키가 정의되어 있는지 확인."""
    assert set(PERIOD_MONTHS.keys()) == {"3m", "6m", "1y", "3y", "5y", "10y", "20y"}


def test_period_months_values_positive():
    for period, months in PERIOD_MONTHS.items():
        assert months > 0, f"{period} 개월 수가 0 이하"


def test_period_months_ordered():
    """기간이 짧은 것에서 긴 것 순서인지 확인."""
    values = list(PERIOD_MONTHS.values())
    assert values == sorted(values)


# ── 상승률 계산 검산 ────────────────────────────────────────────────────

class TestChangePct:
    """_build_snapshot_record 내부 로직을 단독으로 검증."""

    def _calc_change_pct(self, start_price: float, end_price: float) -> Decimal:
        return round(
            Decimal(str((end_price - start_price) / start_price * 100)), 2
        )

    def test_100pct_gain(self):
        result = self._calc_change_pct(1000.0, 2000.0)
        assert result == Decimal("100.00")

    def test_50pct_gain(self):
        result = self._calc_change_pct(1000.0, 1500.0)
        assert result == Decimal("50.00")

    def test_zero_change(self):
        result = self._calc_change_pct(1000.0, 1000.0)
        assert result == Decimal("0.00")

    def test_negative_change(self):
        result = self._calc_change_pct(1000.0, 800.0)
        assert result == Decimal("-20.00")

    def test_realistic_gangnam(self):
        """강남구 실제 사례 근사값 검산.
        2006년 평균 평단가 ≈ 1500만원/㎡, 2024년 ≈ 6000만원/㎡ → +300%
        """
        result = self._calc_change_pct(1500.0, 6000.0)
        assert result == Decimal("300.00")

    def test_precision_preserved(self):
        """소수점 2자리 반올림."""
        result = self._calc_change_pct(1000.0, 1001.005)
        # (1001.005 - 1000) / 1000 * 100 = 0.1005 → 0.10으로 반올림
        assert result == Decimal("0.10")


# ── 데이터 부족 상태 결정 ─────────────────────────────────────────────

class TestDataStatus:
    """_build_snapshot_record가 반환하는 data_status 값 검증.
    실제 로직을 재현해 상태 분기를 테스트한다.
    """

    MIN_TX = 5  # 테스트용 최소 거래 건수

    def _determine_status(
        self,
        start_price, end_price,
        start_tx, end_tx,
        min_tx=5,
    ) -> tuple[str, str | None]:
        import math
        if start_price is None or (isinstance(start_price, float) and math.isnan(start_price)):
            return "no_start", "시작 시점 데이터 없음"
        if end_price is None or (isinstance(end_price, float) and math.isnan(end_price)):
            return "no_end", "종료 시점 데이터 없음"
        if (end_tx or 0) < min_tx:
            return "insufficient", f"거래 건수 부족 ({end_tx}건, 최소 {min_tx}건)"
        if (start_tx or 0) < min_tx:
            return "insufficient", f"시작 시점 거래 건수 부족 ({start_tx}건, 최소 {min_tx}건)"
        if start_price <= 0:
            return "insufficient", "시작 시점 평단가 0 이하"
        return "ok", None

    def test_ok_status(self):
        status, reason = self._determine_status(1000.0, 1200.0, 10, 10)
        assert status == "ok"
        assert reason is None

    def test_no_start(self):
        status, _ = self._determine_status(None, 1200.0, 0, 10)
        assert status == "no_start"

    def test_no_end(self):
        status, _ = self._determine_status(1000.0, None, 10, 0)
        assert status == "no_end"

    def test_insufficient_end_tx(self):
        status, reason = self._determine_status(1000.0, 1200.0, 10, 3)
        assert status == "insufficient"
        assert "3건" in reason

    def test_insufficient_start_tx(self):
        status, reason = self._determine_status(1000.0, 1200.0, 2, 10)
        assert status == "insufficient"
        assert "시작 시점" in reason

    def test_zero_start_price(self):
        status, _ = self._determine_status(0.0, 1200.0, 10, 10)
        assert status == "insufficient"

    def test_exactly_min_tx_is_ok(self):
        """최소 거래 건수 경계값 = 정확히 min_tx면 ok."""
        status, _ = self._determine_status(1000.0, 1200.0, self.MIN_TX, self.MIN_TX)
        assert status == "ok"

    def test_one_below_min_tx_is_insufficient(self):
        """최소 거래 건수 - 1이면 insufficient."""
        status, _ = self._determine_status(1000.0, 1200.0, 10, self.MIN_TX - 1)
        assert status == "insufficient"


# ── 년월 목록 생성 (backfill 유틸) ──────────────────────────────────────

class TestGenerateYearMonths:
    def _generate(self, start_ym: str, end_ym: str) -> list[str]:
        from realestate.jobs.backfill import _generate_year_months
        return _generate_year_months(start_ym, end_ym)

    def test_single_month(self):
        result = self._generate("202406", "202406")
        assert result == ["202406"]

    def test_three_months(self):
        result = self._generate("202404", "202406")
        assert result == ["202404", "202405", "202406"]

    def test_cross_year(self):
        result = self._generate("202311", "202402")
        assert result == ["202311", "202312", "202401", "202402"]

    def test_count_one_year(self):
        result = self._generate("202301", "202312")
        assert len(result) == 12

    def test_count_20_years(self):
        result = self._generate("200601", "202512")
        assert len(result) == 20 * 12

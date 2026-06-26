"""
데이터 수집 정제 로직 단위 테스트.

실제 API 호출 없이 _clean_df 함수만 테스트한다.
손으로 검산 가능한 고정 입력 사용.
"""

import pandas as pd
import pytest

from realestate.batch.collect import _clean_df


# ── 정상 처리 ─────────────────────────────────────────────────────────

def test_clean_df_price_per_sqm(sample_transactions_df):
    """평단가(만원/㎡) 계산이 정확한지 검증."""
    records = _clean_df(sample_transactions_df, "11680", "강남구", "202405")

    # 래미안대치팰리스 84㎡, 8억원 → 80000만원 / 84㎡ ≒ 952.38만원/㎡
    raeimian = [r for r in records if r["apt_name"] == "래미안대치팰리스" and r["deal_amount"] == 80000]
    assert len(raeimian) == 1
    assert float(raeimian[0]["price_per_sqm"]) == pytest.approx(80000 / 84, rel=1e-4)


def test_clean_df_deal_amount_with_comma(sample_transactions_df):
    """거래금액 쉼표 파싱 (80,000 → 80000)."""
    records = _clean_df(sample_transactions_df, "11680", "강남구", "202405")
    amounts = {r["deal_amount"] for r in records}
    assert 80000 in amounts
    assert 90000 in amounts
    assert 120000 in amounts


def test_clean_df_sets_deal_ym(sample_transactions_df):
    """deal_ym이 파라미터 값으로 설정되는지 확인."""
    records = _clean_df(sample_transactions_df, "11680", "강남구", "202405")
    for r in records:
        assert r["deal_ym"] == "202405"


def test_clean_df_returns_five_records(sample_transactions_df):
    """정상 데이터 5건 모두 반환."""
    records = _clean_df(sample_transactions_df, "11680", "강남구", "202405")
    assert len(records) == 5


# ── 취소 거래 필터 ─────────────────────────────────────────────────────

def test_clean_df_removes_cancelled_by_flag(cancelled_transaction_df):
    """해제여부='O' 인 거래는 제외된다."""
    records = _clean_df(cancelled_transaction_df, "11680", "강남구", "202405")
    assert len(records) == 1
    assert records[0]["apt_name"] == "B아파트"


def test_clean_df_removes_cancelled_by_date():
    """해제사유발생일이 있는 거래는 제외된다."""
    df = pd.DataFrame({
        "aptNm": ["취소아파트"],
        "umdNm": ["대치동"],
        "dealAmount": ["50,000"],
        "excluUseAr": ["84.00"],
        "dealYear": ["2024"], "dealMonth": ["05"], "dealDay": ["5"],
        "floor": ["5"], "buildYear": ["2000"],
        "cdealType": [None],
        "cdealDay": ["20240515"],
    })
    records = _clean_df(df, "11680", "강남구", "202405")
    assert len(records) == 0


# ── 이상치 필터 ────────────────────────────────────────────────────────

def test_clean_df_rejects_zero_area():
    """전용면적 0인 레코드는 제외된다."""
    df = pd.DataFrame({
        "aptNm": ["이상한아파트"],
        "umdNm": ["대치동"],
        "dealAmount": ["50,000"],
        "excluUseAr": ["0.00"],
        "dealYear": ["2024"], "dealMonth": ["05"], "dealDay": ["5"],
        "floor": ["5"], "buildYear": ["2000"],
        "cdealType": [None], "cdealDay": [None],
    })
    records = _clean_df(df, "11680", "강남구", "202405")
    assert len(records) == 0


def test_clean_df_rejects_zero_amount():
    """거래금액 0인 레코드는 제외된다."""
    df = pd.DataFrame({
        "aptNm": ["이상한아파트"],
        "umdNm": ["대치동"],
        "dealAmount": ["0"],
        "excluUseAr": ["84.00"],
        "dealYear": ["2024"], "dealMonth": ["05"], "dealDay": ["5"],
        "floor": ["5"], "buildYear": ["2000"],
        "cdealType": [None], "cdealDay": [None],
    })
    records = _clean_df(df, "11680", "강남구", "202405")
    assert len(records) == 0


def test_clean_df_rejects_null_amount():
    """거래금액 null인 레코드는 제외된다."""
    df = pd.DataFrame({
        "aptNm": ["이상한아파트"],
        "umdNm": ["대치동"],
        "dealAmount": [None],
        "excluUseAr": ["84.00"],
        "dealYear": ["2024"], "dealMonth": ["05"], "dealDay": ["5"],
        "floor": ["5"], "buildYear": ["2000"],
        "cdealType": [None], "cdealDay": [None],
    })
    records = _clean_df(df, "11680", "강남구", "202405")
    assert len(records) == 0


def test_clean_df_empty_df_returns_empty():
    """빈 DataFrame 입력 시 빈 목록 반환."""
    records = _clean_df(pd.DataFrame(), "11680", "강남구", "202405")
    assert records == []


def test_clean_df_none_returns_empty():
    """None 입력 시 빈 목록 반환."""
    records = _clean_df(None, "11680", "강남구", "202405")
    assert records == []


# ── 필드 길이 截短 ─────────────────────────────────────────────────────

def test_clean_df_truncates_long_apt_name():
    """apt_name이 100자를 초과하면 자른다."""
    df = pd.DataFrame({
        "aptNm": ["A" * 200],
        "umdNm": ["대치동"],
        "dealAmount": ["50,000"],
        "excluUseAr": ["84.00"],
        "dealYear": ["2024"], "dealMonth": ["05"], "dealDay": ["5"],
        "floor": ["5"], "buildYear": ["2000"],
        "cdealType": [None], "cdealDay": [None],
    })
    records = _clean_df(df, "11680", "강남구", "202405")
    assert len(records) == 1
    assert len(records[0]["apt_name"]) == 100

import pytest


@pytest.fixture
def sample_transactions_df():
    """강남구 202405 실거래 예시 데이터 (검산 가능한 고정값)."""
    import pandas as pd

    # PublicDataReader 1.1.0+ 실제 영문 컬럼명 사용
    return pd.DataFrame({
        "aptNm": ["래미안대치팰리스", "래미안대치팰리스", "타워팰리스", "도곡렉슬", "도곡렉슬"],
        "umdNm": ["대치동", "대치동", "도곡동", "도곡동", "도곡동"],
        "dealAmount": ["80,000", "90,000", "120,000", "70,000", "75,000"],
        "excluUseAr": ["84.00", "84.00", "150.00", "84.00", "84.00"],
        "dealYear": ["2024", "2024", "2024", "2024", "2024"],
        "dealMonth": ["05", "05", "05", "05", "05"],
        "dealDay": ["10", "15", "20", "5", "25"],
        "floor": ["10", "15", "30", "8", "12"],
        "buildYear": ["2002", "2002", "2003", "2003", "2003"],
        "cdealType": [None, None, None, None, None],
        "cdealDay": [None, None, None, None, None],
    })


@pytest.fixture
def cancelled_transaction_df():
    """취소된 거래 포함 데이터."""
    import pandas as pd

    return pd.DataFrame({
        "aptNm": ["A아파트", "B아파트"],
        "umdNm": ["대치동", "대치동"],
        "dealAmount": ["50,000", "60,000"],
        "excluUseAr": ["84.00", "84.00"],
        "dealYear": ["2024", "2024"],
        "dealMonth": ["05", "05"],
        "dealDay": ["5", "10"],
        "floor": ["5", "10"],
        "buildYear": ["2000", "2001"],
        "cdealType": ["O", None],   # 첫 번째 취소 거래
        "cdealDay": ["20240520", None],
    })

"""
금융 계산 모듈.

모든 함수는 pandas 벡터 연산으로 구현한다.
종목별 루프를 돌리면 종목 수 × 기간에 비례해 속도가 선형 저하되므로
pivot 후 행렬 단위로 처리한다.

입력 데이터프레임 공통 전제:
  - index: DatetimeIndex (날짜), columns: ticker
  - 값: 수정주가(adjusted close)
  - 결측값(NaN)은 호출 전에 처리 완료(ffill 등)되어 있어야 한다.
"""

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252
DISCLAIMER = "투자 조언이 아닙니다. FomoBot은 지나간 걸 보여줄 뿐이에요."


def compute_returns(price_matrix: pd.DataFrame) -> pd.Series:
    """
    각 종목의 기간 수익률(%) 계산.

    수익률 = (마지막 종가 / 첫 종가 - 1) × 100

    Parameters
    ----------
    price_matrix : pd.DataFrame
        index=날짜(DatetimeIndex), columns=ticker, 값=수정주가

    Returns
    -------
    pd.Series  index=ticker, 값=수익률(%)
    """
    if price_matrix.empty or len(price_matrix) < 2:
        return pd.Series(dtype=float)

    first_valid = price_matrix.apply(lambda col: col.dropna().iloc[0] if col.notna().any() else np.nan)
    last_valid = price_matrix.apply(lambda col: col.dropna().iloc[-1] if col.notna().any() else np.nan)

    return (last_valid / first_valid - 1) * 100


def compute_mdd(price_matrix: pd.DataFrame) -> pd.Series:
    """
    각 종목의 기간 내 최대낙폭(MDD, %) 계산.

    MDD = min((종가 - 누적고점) / 누적고점) × 100
    값은 음수로 반환 (예: -15.3 → 15.3% 낙폭).

    Parameters
    ----------
    price_matrix : pd.DataFrame

    Returns
    -------
    pd.Series  index=ticker, 값=MDD(%) ≤ 0
    """
    if price_matrix.empty:
        return pd.Series(dtype=float)

    rolling_max = price_matrix.cummax()
    drawdown = (price_matrix - rolling_max) / rolling_max * 100
    return drawdown.min()


def compute_volatility(price_matrix: pd.DataFrame) -> pd.Series:
    """
    각 종목의 연율화 변동성(%) 계산.

    변동성 = 일간 수익률 표준편차 × √252 × 100

    Parameters
    ----------
    price_matrix : pd.DataFrame

    Returns
    -------
    pd.Series  index=ticker, 값=연율화 변동성(%)
    """
    if price_matrix.empty or len(price_matrix) < 2:
        return pd.Series(dtype=float)

    daily_returns = price_matrix.pct_change().dropna(how="all")
    return daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100


def compute_excess_return(
    stock_returns: pd.Series,
    index_price_series: pd.Series,
) -> pd.Series:
    """
    지수 대비 초과수익률(%) 계산.

    초과수익 = 종목 수익률 - 지수 수익률

    Parameters
    ----------
    stock_returns : pd.Series  index=ticker, 값=종목 수익률(%)
    index_price_series : pd.Series
        index=날짜(DatetimeIndex), 값=지수 수정주가 (시작~끝)

    Returns
    -------
    pd.Series  index=ticker, 값=초과수익률(%)
    """
    if index_price_series.empty or len(index_price_series) < 2:
        return stock_returns * np.nan

    first = index_price_series.dropna().iloc[0]
    last = index_price_series.dropna().iloc[-1]
    index_return = (last / first - 1) * 100

    return stock_returns - index_return


def build_ranking_df(
    price_matrix: pd.DataFrame,
    index_price_series: pd.Series,
    top: int | None = None,
) -> pd.DataFrame:
    """
    수익률·MDD·변동성·초과수익을 한 번에 계산해 랭킹 DataFrame 반환.

    Parameters
    ----------
    price_matrix : pd.DataFrame
        index=날짜, columns=ticker, 값=수정주가
    index_price_series : pd.Series
        지수 수정주가 시리즈 (같은 날짜 범위)
    top : int | None
        상위 N개 반환. None이면 필터 통과 종목 전체 저장 (하락률 상위 지원용).

    Returns
    -------
    pd.DataFrame
        columns: [rank, ticker, return_pct, mdd_pct,
                  volatility_annualized_pct, excess_return_pct]
    """
    returns = compute_returns(price_matrix)
    mdd = compute_mdd(price_matrix)
    volatility = compute_volatility(price_matrix)
    excess = compute_excess_return(returns, index_price_series)

    result = pd.DataFrame({
        "return_pct": returns,
        "mdd_pct": mdd,
        "volatility_annualized_pct": volatility,
        "excess_return_pct": excess,
    })

    result = (
        result.dropna(subset=["return_pct"])
        .sort_values("return_pct", ascending=False)
        .reset_index()
        .rename(columns={"index": "ticker"})
    )
    if top is not None:
        result = result.head(top)
    result.insert(0, "rank", range(1, len(result) + 1))
    return result


PERIOD_TO_DAYS: dict[str, int] = {
    "1d": 1,
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "365d": 365,
    "1825d": 1825,
}

# "데이터 공백형"(gap) 판정 임계 — first_valid_date가 윈도우 길이의 이 비율 이상
# 늦으면 "N일 수익률"이 실제로는 그보다 훨씬 짧은 기간 대비라고 본다. 순수 비율
# 기준(절대일수 아님) — 절대일수를 쓰면 7d에서 과하게 걸리고 1825d에서 거의
# 안 걸리는 문제가 있어(조사 단계에서 사용자가 지적) 기간 무관하게 동일 기준을
# 적용할 수 있는 비율을 택했다.
GAP_LAG_RATIO_THRESHOLD = 0.2


def compute_start_validity(
    price_matrix: pd.DataFrame,
    volume_matrix: pd.DataFrame,
    window_start_date: pd.Timestamp,
    period_days: int,
) -> pd.DataFrame:
    """
    각 종목의 기간 수익률(compute_returns의 first_valid)이 실제로 요청한
    기간 전체를 대표하는지 판정한다. return_pct 등 다른 계산에는 전혀
    관여하지 않는 표시용 메타데이터 전용 함수 — price_matrix/volume_matrix를
    읽기만 하고 수정하지 않는다.

    002210(halt 중 조용한 basis 변경) 사고로 두 가지 서로 다른 원인이 있다는
    게 드러났다 — 하나의 조건으로는 못 잡는다:
      (A) 'gap'(데이터 공백형): 그 종목의 데이터 자체가 윈도우 시작일에는
          아직 없었다(신규상장 등) — first_valid_date가 window_start_date보다
          GAP_LAG_RATIO_THRESHOLD 이상 늦다.
      (B) 'halted'(정지 시작형): 데이터(행)는 있지만 그 시작값이 실거래가
          아니다(volume=0, 정지 중 동결값) — 002210이 이 경우였다. 이 경우
          first_valid_date는 window_start_date와 거의 같아(행 자체는 존재)
          (A)로는 전혀 안 잡히므로 volume을 직접 확인해야 한다.
    두 조건이 동시에 해당하면 'halted'를 우선한다(더 구체적인 설명이므로).
    volume=0 여부는 임계값이 필요 없는 사실 판정이라 별도 비율 기준이 없다.

    Parameters
    ----------
    price_matrix : pd.DataFrame   index=날짜, columns=ticker, 값=close_adj
    volume_matrix : pd.DataFrame  index=날짜, columns=ticker, 값=volume (price_matrix와 동일 shape)
    window_start_date : pd.Timestamp  이 기간 계산에 실제 쓰인 start_date(거래일 스냅 후)
    period_days : int  PERIOD_TO_DAYS의 값(예: 30, 365) — 비율 계산의 분모

    Returns
    -------
    pd.DataFrame  index=ticker, columns=[first_valid_date, start_validity]
      start_validity: "gap" | "halted" 뿐(해당 없으면 그 종목은 결과에 없음 —
      호출부가 반드시 결측을 "정상"으로 처리해야 한다는 뜻).
    """
    if price_matrix.empty or period_days <= 0:
        return pd.DataFrame(columns=["first_valid_date", "start_validity"])

    records: dict[str, tuple] = {}
    for ticker in price_matrix.columns:
        first_valid_date = price_matrix[ticker].first_valid_index()
        if first_valid_date is None:
            continue

        first_valid_volume = None
        if ticker in volume_matrix.columns:
            vol = volume_matrix.at[first_valid_date, ticker]
            first_valid_volume = None if pd.isna(vol) else vol

        if first_valid_volume is not None and first_valid_volume == 0:
            records[ticker] = (first_valid_date.date(), "halted")
            continue

        lag_days = (first_valid_date - window_start_date).days
        if lag_days / period_days >= GAP_LAG_RATIO_THRESHOLD:
            records[ticker] = (first_valid_date.date(), "gap")

    return pd.DataFrame.from_dict(
        records, orient="index", columns=["first_valid_date", "start_validity"]
    )


def compute_quote_metrics(prices: pd.Series) -> dict:
    """
    단일 종목 가격 시계열에서 수익률·MDD·변동성을 계산한다.

    Parameters
    ----------
    prices : pd.Series
        index=DatetimeIndex, 값=수정주가(float)

    Returns
    -------
    dict with keys: return_pct, mdd_pct, volatility_annualized_pct
        값이 계산 불가(데이터 부족)이면 None.
    """
    if prices.empty or len(prices) < 2:
        return {"return_pct": None, "mdd_pct": None, "volatility_annualized_pct": None}

    pm = prices.to_frame("_ticker")

    ret = compute_returns(pm)
    mdd = compute_mdd(pm)
    vol = compute_volatility(pm)

    return {
        "return_pct": float(ret.iloc[0]) if not ret.empty else None,
        "mdd_pct": float(mdd.iloc[0]) if not mdd.empty else None,
        "volatility_annualized_pct": float(vol.iloc[0]) if not vol.empty else None,
    }

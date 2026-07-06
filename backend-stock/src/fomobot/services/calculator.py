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

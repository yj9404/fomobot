"""
노이즈 필터.

동전주·잡주·저유동성 종목을 랭킹 대상에서 제거한다.
기준값은 config.py(pydantic-settings)로 외부화되어 있으므로
코드 변경 없이 .env로 조정 가능하다.
"""

import logging

import numpy as np
import pandas as pd

from fomobot.config import settings

TRADING_DAYS_PER_YEAR = 252

logger = logging.getLogger(__name__)


def apply_kospi_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    KOSPI 종목 필터링.

    Parameters
    ----------
    df : pd.DataFrame
        columns 필수: ticker, market_cap, avg_volume_30d, close_adj
        각 값은 해당 종목의 최근 기준값 (배치에서 집계 후 전달).

    Returns
    -------
    필터 통과 종목만 담긴 DataFrame
    """
    before = len(df)

    mask = (
        (df["market_cap"] >= settings.kospi_min_market_cap)
        & (df["avg_volume_30d"] >= settings.kospi_min_avg_volume_30d)
        & (df["close_adj"] >= settings.kospi_min_price)
    )
    result = df[mask].copy()

    logger.info(
        "KOSPI 필터: %d → %d종목 (제거 %d, 시총≥%s억 / 거래대금≥%s억 / 가격≥%s원)",
        before, len(result), before - len(result),
        settings.kospi_min_market_cap // 100_000_000,
        settings.kospi_min_avg_volume_30d // 100_000_000,
        settings.kospi_min_price,
    )
    return result


def apply_nasdaq_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    NASDAQ 종목 필터링.

    Parameters
    ----------
    df : pd.DataFrame
        columns 필수: ticker, market_cap, avg_volume_30d, close_adj
        market_cap, avg_volume_30d 단위: USD

    Returns
    -------
    필터 통과 종목만 담긴 DataFrame
    """
    before = len(df)

    # market_cap 필터:
    # - nasdaq_exclude_unknown_market_cap=True : 0(미수집)이면 보수적으로 제외
    # - nasdaq_exclude_unknown_market_cap=False: 기존 동작 — 0이면 시총 조건 생략
    if settings.nasdaq_exclude_unknown_market_cap:
        cap_mask = (df["market_cap"] > 0) & (df["market_cap"] >= settings.nasdaq_min_market_cap_usd)
    else:
        cap_mask = (df["market_cap"] == 0) | (df["market_cap"] >= settings.nasdaq_min_market_cap_usd)

    mask = (
        cap_mask
        & (df["avg_volume_30d"] >= settings.nasdaq_min_avg_volume_30d_usd)
        & (df["close_adj"] >= settings.nasdaq_min_price_usd)
    )
    result = df[mask].copy()

    unknown_cap_count = int((df["market_cap"] == 0).sum())
    logger.info(
        "NASDAQ 필터: %d → %d종목 (제거 %d, 시총≥$%sM / 거래대금≥$%sM / 가격≥$%s, 시총미확인 %d종목)",
        before, len(result), before - len(result),
        settings.nasdaq_min_market_cap_usd // 1_000_000,
        settings.nasdaq_min_avg_volume_30d_usd // 1_000_000,
        settings.nasdaq_min_price_usd,
        unknown_cap_count,
    )
    return result


def apply_price_sanity_filter(price_matrix: pd.DataFrame) -> pd.DataFrame:
    """
    corporate action(액면분할·병합) 왜곡 종목을 price_matrix에서 제거.

    두 가지 조건 중 하나라도 해당하면 데이터 오염 종목으로 간주한다:
      1. 단일 거래일 pct_change 절댓값 > nasdaq_max_daily_move_pct (기본 3.0 = 300%)
      2. 연율화 변동성 > nasdaq_max_volatility_pct (기본 1000%)

    Parameters
    ----------
    price_matrix : pd.DataFrame
        index=날짜(DatetimeIndex), columns=ticker, 값=수정주가

    Returns
    -------
    오염 의심 종목이 제거된 price_matrix
    """
    if price_matrix.empty or len(price_matrix) < 2:
        return price_matrix

    daily_returns = price_matrix.pct_change()

    # 1. 단일 거래일 변동률 임계값 초과
    max_daily = settings.nasdaq_max_daily_move_pct
    extreme_move_mask = (daily_returns.abs() > max_daily).any()
    removed_by_move = set(extreme_move_mask[extreme_move_mask].index.tolist())

    # 2. 연율화 변동성 임계값 초과
    max_vol = settings.nasdaq_max_volatility_pct
    annualized_vol = daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
    removed_by_vol = set(annualized_vol[annualized_vol > max_vol].index.tolist())

    all_removed = removed_by_move | removed_by_vol
    only_vol = removed_by_vol - removed_by_move  # 변동률은 통과했지만 변동성에서 걸린 종목

    if removed_by_move:
        logger.warning(
            "NASDAQ sanity 필터 — 단일 거래일 변동률 >%.0f%% 종목 %d개 제외: %s",
            max_daily * 100,
            len(removed_by_move),
            sorted(removed_by_move)[:20],
        )
    if only_vol:
        logger.warning(
            "NASDAQ sanity 필터 — 연율화 변동성 >%.0f%% 종목 %d개 추가 제외: %s",
            max_vol,
            len(only_vol),
            sorted(only_vol)[:20],
        )
    if all_removed:
        keep = [t for t in price_matrix.columns if t not in all_removed]
        return price_matrix[keep]

    return price_matrix


def drop_low_data_tickers(
    price_matrix: pd.DataFrame,
    max_missing_ratio: float = 0.20,
) -> pd.DataFrame:
    """
    기간 내 결측률이 임계값을 초과하는 종목을 제거.

    상장 기간이 짧거나 거래 정지 종목이 랭킹을 오염하는 것을 방지한다.

    Parameters
    ----------
    price_matrix : pd.DataFrame
        index=날짜, columns=ticker, 값=수정주가
    max_missing_ratio : float
        허용 최대 결측률 (기본 20%)

    Returns
    -------
    결측률 ≤ max_missing_ratio 인 종목만 남긴 DataFrame
    """
    missing_ratio = price_matrix.isna().mean()
    valid_tickers = missing_ratio[missing_ratio <= max_missing_ratio].index
    dropped = len(price_matrix.columns) - len(valid_tickers)
    if dropped:
        logger.warning("결측률 초과로 %d개 종목 제외 (기준 %.0f%%)", dropped, max_missing_ratio * 100)
    return price_matrix[valid_tickers]

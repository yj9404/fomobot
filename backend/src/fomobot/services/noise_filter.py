"""
노이즈 필터.

동전주·잡주·저유동성 종목을 랭킹 대상에서 제거한다.
기준값은 config.py(pydantic-settings)로 외부화되어 있으므로
코드 변경 없이 .env로 조정 가능하다.
"""

import logging
import pandas as pd

from fomobot.config import settings

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

    mask = (
        (df["market_cap"] >= settings.nasdaq_min_market_cap_usd)
        & (df["avg_volume_30d"] >= settings.nasdaq_min_avg_volume_30d_usd)
        & (df["close_adj"] >= settings.nasdaq_min_price_usd)
    )
    result = df[mask].copy()

    logger.info(
        "NASDAQ 필터: %d → %d종목 (제거 %d, 시총≥$%sM / 거래대금≥$%sM / 가격≥$%s)",
        before, len(result), before - len(result),
        settings.nasdaq_min_market_cap_usd // 1_000_000,
        settings.nasdaq_min_avg_volume_30d_usd // 1_000_000,
        settings.nasdaq_min_price_usd,
    )
    return result


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

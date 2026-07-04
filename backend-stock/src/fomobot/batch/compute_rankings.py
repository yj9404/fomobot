"""
랭킹 계산 배치.

수집 배치 완료 후 트리거된다.
price_daily 테이블에서 필요한 기간의 데이터를 읽어
수익률·MDD·변동성·초과수익을 pandas 벡터 연산으로 계산 후
ranking_snapshot 테이블에 저장한다.

요청 시 실시간 계산 금지 — API는 이 테이블만 조회한다.
"""

import logging
import time
from datetime import date, timedelta

import pandas as pd

from fomobot.db.crud import (
    get_index_range_sync,
    get_last_trading_day_sync,
    get_price_range_sync,
    upsert_ranking_snapshots_sync,
)
from fomobot.db.session import SyncSessionLocal
from fomobot.services.calculator import (
    PERIOD_TO_DAYS,
    build_ranking_df,
)
from fomobot.services.noise_filter import (
    apply_kospi_filter,
    apply_nasdaq_filter,
    apply_price_sanity_filter,
    drop_low_data_tickers,
)

logger = logging.getLogger(__name__)

MARKET_CONFIG = {
    "kospi": {
        "index_code": "KOSPI",
        "filter_fn": apply_kospi_filter,
        "sanity_filter_fn": None,
    },
    "nasdaq": {
        "index_code": "QQQ",
        "filter_fn": apply_nasdaq_filter,
        "sanity_filter_fn": apply_price_sanity_filter,
    },
}


def _fetch_nasdaq_market_caps(tickers: list[str]) -> dict[str, int | None]:
    """NASDAQ 상위 종목 시총을 yfinance fast_info로 조회한다."""
    import yfinance as yf
    caps: dict[str, int | None] = {}
    for ticker in tickers:
        try:
            cap = yf.Ticker(ticker).fast_info.market_cap
            caps[ticker] = int(cap) if cap else None
        except Exception:
            caps[ticker] = None
        time.sleep(0.05)
    logger.info("NASDAQ 시총 조회 완료: %d종목", len(caps))
    return caps


def _fetch_name_map(market: str, tickers: list[str]) -> dict[str, str]:
    """티커 → 종목명 딕셔너리를 반환한다. 실패 시 ticker를 name으로 사용."""
    name_map: dict[str, str] = {}
    if market == "kospi":
        try:
            from pykrx import stock as krx
            for ticker in tickers:
                try:
                    name_map[ticker] = krx.get_market_ticker_name(ticker)
                except Exception:
                    name_map[ticker] = ticker
        except Exception:
            logger.warning("pykrx 종목명 조회 실패")
    elif market == "nasdaq":
        try:
            import io
            import httpx
            resp = httpx.get(
                "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
                timeout=30,
            )
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text), sep="|")
            df = df[df["Symbol"].notna() & ~df["Symbol"].str.startswith("File", na=False)]
            ticker_set = set(tickers)
            name_col = "Security Name" if "Security Name" in df.columns else df.columns[1]
            for _, row in df.iterrows():
                sym = str(row["Symbol"]).strip()
                if sym in ticker_set:
                    name_map[sym] = str(row[name_col]).strip()[:200]
        except Exception:
            logger.warning("NASDAQ 종목명 조회 실패")
    return name_map


def _load_price_matrix(
    session,
    market: str,
    start_date: date,
    end_date: date,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    DB에서 가격 데이터를 읽어 (price_matrix, meta_df) 반환.

    price_matrix: index=날짜, columns=ticker, 값=close_adj
    meta_df:      columns=[ticker, market_cap, avg_volume_30d, close_adj]
                  (노이즈 필터용, 최근 30일 평균 거래대금은 여기서 계산)
    """
    rows = get_price_range_sync(session, market, start_date, end_date)
    if not rows:
        return pd.DataFrame(), pd.DataFrame()

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])

    # pivot: 날짜 × 종목
    price_matrix = df.pivot(index="date", columns="ticker", values="close_adj")
    price_matrix = price_matrix.sort_index()

    # 메타: 최신 날짜 기준 시총 + 최근 30일 평균 거래대금
    cutoff_30d = end_date - timedelta(days=30)
    recent = df[df["date"] >= pd.Timestamp(cutoff_30d)]

    meta = (
        df[df["date"] == df["date"].max()]
        .groupby("ticker")
        .agg(
            market_cap=("market_cap", "last"),
            close_adj=("close_adj", "last"),
        )
        .reset_index()
    )

    # 거래대금(KRW) = volume(주) × close_adj(원) — 필터 임계값과 단위 일치
    recent_with_value = recent.copy()
    recent_with_value["trading_value"] = recent_with_value["volume"] * recent_with_value["close_adj"]
    avg_vol = (
        recent_with_value.groupby("ticker")["trading_value"]
        .mean()
        .rename("avg_volume_30d")
        .reset_index()
    )
    meta = meta.merge(avg_vol, on="ticker", how="left")
    meta["avg_volume_30d"] = meta["avg_volume_30d"].fillna(0)
    meta["market_cap"] = meta["market_cap"].fillna(0)

    return price_matrix, meta


def compute_rankings_for_market(
    market: str,
    snapshot_date: date | None = None,
    periods: list[str] | None = None,
    top: int = 100,
) -> int:
    """
    특정 마켓의 랭킹을 계산해 DB에 저장한다.

    Parameters
    ----------
    market : str        "kospi" | "nasdaq"
    snapshot_date : date | None
        랭킹 기준일. None이면 price_daily 기준 실제 최근 거래일로 자동 계산한다
        (date.today()를 쓰면 휴장일 실행 시 "1d" 구간이 항상 빈 결과가 됨).
    periods : list[str] | None
        계산할 기간 목록. None이면 PERIOD_TO_DAYS 전체(1d~1825d)를 계산한다
        (정기 cron·수동 backfill이 쓰는 기존 동작 그대로 — 반드시 보존해야 함,
        회귀 시 정기 배치가 조용히 깨지므로 tests/test_compute_rankings.py로 고정해둠).
        일부만 지정하면 그 기간만 계산·저장하고 나머지 기간의 기존 스냅샷은
        건드리지 않는다 (gap-fill이 "비어있는 기간만" 채우기 위해 사용).
    top : int           저장할 상위 종목 수 (기본 100, API에서 최대 top=100 지원)
    """
    config = MARKET_CONFIG.get(market)
    if config is None:
        raise ValueError(f"지원하지 않는 마켓: {market}")

    period_items = (
        list(PERIOD_TO_DAYS.items())
        if periods is None
        else [(p, PERIOD_TO_DAYS[p]) for p in periods]
    )

    all_snapshot_records: list[dict] = []

    with SyncSessionLocal() as session:
        if snapshot_date is None:
            snapshot_date = get_last_trading_day_sync(session, market)
        if snapshot_date is None:
            logger.warning("%s: price_daily에 데이터가 없어 랭킹 계산을 스킵합니다.", market)
            return 0

        for period_key, days in period_items:
            try:
                raw_start_date = snapshot_date - timedelta(days=days)
                # 캘린더 일수로 뺀 값은 비거래일(주말 등)에 떨어질 수 있다 — 특히
                # "1d"는 snapshot_date가 월요일이면 raw_start_date가 일요일이 되어
                # 그 구간에 거래일이 1개(당일)뿐이 되고, compute_returns가 데이터
                # 부족으로 빈 결과를 반환해 해당 기간이 통째로 0건이 된다
                # (모든 월요일에 재발하는 구조적 버그였음 — 실제 거래일로 스냅해 해결).
                start_date = (
                    get_last_trading_day_sync(session, market, as_of=raw_start_date)
                    or raw_start_date
                )

                price_matrix, meta_df = _load_price_matrix(
                    session, market, start_date, snapshot_date
                )
                # KOSPI는 meta_df에 실제 시총이 있음; NASDAQ는 0으로 채워져 있으므로 None 처리
                cap_from_meta: dict[str, int | None] = {}
                if not meta_df.empty and market == "kospi":
                    cap_from_meta = {
                        row["ticker"]: (int(row["market_cap"]) if row["market_cap"] > 0 else None)
                        for _, row in meta_df.iterrows()
                    }

                if price_matrix.empty:
                    logger.warning("%s %s: 데이터 없음, 스킵", market, period_key)
                    continue

                # 결측률 높은 종목 제거
                price_matrix = drop_low_data_tickers(price_matrix)
                if price_matrix.empty:
                    continue

                # 가격 sanity 필터: corporate action(액면분할·병합) 왜곡 종목 제거
                sanity_fn = config.get("sanity_filter_fn")
                if sanity_fn is not None:
                    price_matrix = sanity_fn(price_matrix)
                    if price_matrix.empty:
                        logger.warning("%s %s: sanity 필터 후 종목 없음", market, period_key)
                        continue

                # 노이즈 필터 (메타 기준)
                if not meta_df.empty:
                    filtered_meta = config["filter_fn"](meta_df)
                    valid_tickers = filtered_meta["ticker"].tolist()
                    price_matrix = price_matrix[
                        [t for t in valid_tickers if t in price_matrix.columns]
                    ]

                if price_matrix.empty:
                    logger.warning("%s %s: 필터 후 종목 없음", market, period_key)
                    continue

                # 지수 가격
                index_rows = get_index_range_sync(
                    session, config["index_code"], start_date, snapshot_date
                )
                if index_rows:
                    idx_series = pd.Series(
                        {pd.Timestamp(r["date"]): r["close_adj"] for r in index_rows}
                    )
                else:
                    idx_series = pd.Series(dtype=float)

                # 랭킹 계산 (벡터 연산)
                ranking_df = build_ranking_df(price_matrix, idx_series, top=top)

                # snapshot_date 당일 종가 맵 (ticker → close_adj).
                # price_matrix의 마지막 행(= snapshot_date)에서 추출.
                # as_of 시점 주가를 스냅샷에 저장해 두면, 백테스트가
                # price_daily 과거분 없이도 기준 주가를 참조할 수 있다.
                last_row = price_matrix.iloc[-1]  # snapshot_date 행

                period_records: list[dict] = []
                for _, row in ranking_df.iterrows():
                    ticker_str = str(row["ticker"])
                    close_at_snapshot = last_row.get(ticker_str)
                    period_records.append({
                        "snapshot_date": snapshot_date,
                        "market": market,
                        "period": period_key,
                        "rank": int(row["rank"]),
                        "ticker": ticker_str,
                        "name": None,
                        "return_pct": float(row["return_pct"]),
                        "mdd_pct": float(row["mdd_pct"]) if pd.notna(row["mdd_pct"]) else None,
                        "volatility_annualized_pct": (
                            float(row["volatility_annualized_pct"])
                            if pd.notna(row["volatility_annualized_pct"]) else None
                        ),
                        "excess_return_pct": (
                            float(row["excess_return_pct"])
                            if pd.notna(row["excess_return_pct"]) else None
                        ),
                        "close_price_at_snapshot": (
                            float(close_at_snapshot)
                            if close_at_snapshot is not None and pd.notna(close_at_snapshot)
                            else None
                        ),
                        "market_cap": cap_from_meta.get(ticker_str),
                    })

                # period별 즉시 저장 (이후 period 실패해도 앞 데이터 보존)
                if period_records:
                    upsert_ranking_snapshots_sync(session, period_records)
                    all_snapshot_records.extend(period_records)

                logger.info(
                    "%s %s 랭킹 계산·저장 완료: %d종목",
                    market, period_key, len(period_records),
                )
            except Exception:
                # 한 기간의 실패가 나머지 기간 전체를 무산시키지 않도록 격리.
                logger.exception("%s %s 랭킹 계산 실패 — 다음 기간으로 진행", market, period_key)
                continue

    if all_snapshot_records:
        unique_tickers = list({r["ticker"] for r in all_snapshot_records})
        name_map = _fetch_name_map(market, unique_tickers)

        # NASDAQ: yfinance fast_info로 상위 종목 시총 조회 후 반영
        cap_map: dict[str, int | None] = {}
        if market == "nasdaq":
            cap_map = _fetch_nasdaq_market_caps(unique_tickers)

        with SyncSessionLocal() as session:
            final_records = [
                {
                    **r,
                    "name": name_map.get(r["ticker"], r["ticker"])[:200],
                    **({"market_cap": cap_map.get(r["ticker"])} if market == "nasdaq" else {}),
                }
                for r in all_snapshot_records
            ]
            upsert_ranking_snapshots_sync(session, final_records)
        logger.info(
            "%s 랭킹 스냅샷 %d건 저장 완료 (기준일: %s)",
            market, len(all_snapshot_records), snapshot_date,
        )

    return len(all_snapshot_records)


def run_rankings_today() -> None:
    """최근 거래일 기준으로 KOSPI + NASDAQ 랭킹을 모두 계산한다."""
    for market in ("kospi", "nasdaq"):
        try:
            compute_rankings_for_market(market, top=300)
        except Exception:
            logger.exception("%s 랭킹 계산 중 오류", market)

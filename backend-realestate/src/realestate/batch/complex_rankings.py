"""
단지 단위 랭킹 계산 배치.

re_transaction 원천 데이터에서 윈도우 기반으로
단지별 면적당 평단가 중위값과 상승률을 계산해 re_complex_ranking_snapshot에 저장한다.

윈도우 정책 (N = settings.re_window_months, 기본 3):
  - 시작 앵커 (3m 제외): [start_ym - N, start_ym + N]  (7개월 대칭)
  - 시작 앵커 (3m만):     [start_ym - N, start_ym]     (4개월, 과거 방향만)
    → 3m 구간에서 start_ym + N ≥ end_ym 이므로 겹침 방지
  - 종료 앵커 (공통):     [end_ym - N, end_ym]          (4개월, 미래 방향 차단)

최소 거래건수 M = settings.re_min_tx_per_window (기본 3):
  시작·종료 앵커 양쪽 모두 M건 이상이어야 data_status='ok'.
"""

import logging
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import text

from realestate.batch.normalize import make_complex_key, normalize_apt_name
from realestate.batch.regions import SIGUNGU_MAP
from realestate.config import settings
from realestate.db.crud import (
    get_sigungu_names_sync,
    upsert_complex_ranking_snapshots_sync,
)
from realestate.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)

PERIOD_MONTHS: dict[str, int] = {
    "3m": 3,
    "6m": 6,
    "1y": 12,
    "3y": 36,
    "5y": 60,
    "10y": 120,
    "20y": 240,
}

# 3m 구간은 시작 앵커가 과거 방향만 → 종료 앵커와 1개월 겹침 가능
_OVERLAP_PERIODS = {"3m"}


def subtract_months(ym: str, months: int) -> str:
    """YYYYMM에서 months 개월을 뺀 YYYYMM을 반환한다."""
    year, month = int(ym[:4]), int(ym[4:])
    month -= months
    while month <= 0:
        month += 12
        year -= 1
    return f"{year}{month:02d}"


def add_months(ym: str, months: int) -> str:
    """YYYYMM에 months 개월을 더한 YYYYMM을 반환한다."""
    year, month = int(ym[:4]), int(ym[4:])
    month += months
    while month > 12:
        month -= 12
        year += 1
    return f"{year}{month:02d}"


def get_end_ym() -> str:
    """랭킹 기준 완성월 = 전전월 (신고 시차 2개월 여유)."""
    from datetime import date
    today = date.today()
    month = today.month - 2
    year = today.year
    if month <= 0:
        month += 12
        year -= 1
    return f"{year}{month:02d}"


def _get_windows(
    period: str, start_ym: str, end_ym: str, n: int
) -> tuple[tuple[str, str], tuple[str, str], bool]:
    """
    (start_window, end_window, windows_overlap)을 반환한다.

    종료 앵커: 공통 [end-n, end]  (미래 방향 차단)
    시작 앵커 결정 규칙:
      - 기간(월수) > 2n : 대칭 [start-n, start+n]  → 종료 앵커와 겹치지 않음
      - 기간(월수) ≤ 2n : 과거 방향만 [start-n, start] → 겹침 최소화
        (3m: P=3 ≤ 2×3=6, 6m: P=6 ≤ 2×3=6 해당)
    """
    end_w: tuple[str, str] = (subtract_months(end_ym, n), end_ym)

    period_months_val = PERIOD_MONTHS.get(period, 0)
    if period_months_val <= 2 * n:
        # 과거 방향만 → 겹침 없음 (1개월 인접 허용)
        start_w: tuple[str, str] = (subtract_months(start_ym, n), start_ym)
    else:
        start_w = (subtract_months(start_ym, n), add_months(start_ym, n))

    # 겹침: start_w 끝 >= end_w 시작이면 공유 월 존재
    overlap = start_w[1] >= end_w[0]
    return start_w, end_w, overlap


def _load_transactions_window(
    session, window_start: str, window_end: str
) -> pd.DataFrame:
    """수도권 전체 대상으로 윈도우 내 유효 거래를 로드한다."""
    sql = text("""
        SELECT sigungu_code, eupmyeondong, apt_name, deal_ym, price_per_sqm, deal_amount
        FROM re_transaction
        WHERE deal_ym BETWEEN :start AND :end
          AND price_per_sqm > 0
    """)
    result = session.execute(sql, {"start": window_start, "end": window_end})
    rows = [dict(r._mapping) for r in result]
    if not rows:
        return pd.DataFrame(
            columns=["sigungu_code", "eupmyeondong", "apt_name", "deal_ym", "price_per_sqm", "deal_amount"]
        )
    df = pd.DataFrame(rows)
    df["price_per_sqm"] = df["price_per_sqm"].astype(float)
    df["deal_amount"] = df["deal_amount"].astype(float)
    return df


def _add_complex_key(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame에 apt_name_norm, complex_key 컬럼을 추가한다."""
    df = df.copy()
    df["apt_name_norm"] = df["apt_name"].apply(normalize_apt_name)
    df["complex_key"] = df.apply(
        lambda r: make_complex_key(r["sigungu_code"], r["eupmyeondong"], r["apt_name_norm"]),
        axis=1,
    )
    return df


def _compute_window_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    complex_key 단위로 중위 평단가·중위 거래금액·거래건수를 집계한다.

    반환 컬럼: complex_key, median_price, median_deal_amount, tx_count,
               sigungu_code, eupmyeondong, apt_name, apt_name_norm
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "complex_key", "median_price", "median_deal_amount", "tx_count",
            "sigungu_code", "eupmyeondong", "apt_name", "apt_name_norm",
        ])

    meta = (
        df.groupby("complex_key")
        .agg(
            sigungu_code=("sigungu_code", "last"),
            eupmyeondong=("eupmyeondong", "last"),
            apt_name=("apt_name", "last"),
            apt_name_norm=("apt_name_norm", "last"),
        )
        .reset_index()
    )
    stats = (
        df.groupby("complex_key")
        .agg(
            median_price=("price_per_sqm", "median"),
            median_deal_amount=("deal_amount", "median"),
            tx_count=("price_per_sqm", "count"),
        )
        .reset_index()
    )
    return meta.merge(stats, on="complex_key")


def _get_complex_display_name(
    sigungu_code: str, sigungu_name: str, eupmyeondong: str, apt_name: str
) -> str:
    sg = SIGUNGU_MAP.get(sigungu_code, {})
    sido = sg.get("sido", "")
    return f"{sido} {sigungu_name} {eupmyeondong} {apt_name}".strip()


def _determine_status(
    start_price: float | None,
    end_price: float | None,
    start_tx: int | None,
    end_tx: int | None,
    min_tx: int,
    start_w: tuple[str, str],
    end_w: tuple[str, str],
) -> tuple[str, str | None, Decimal | None]:
    """(data_status, insufficient_reason, change_pct)를 반환한다."""
    if start_price is None:
        return "no_start", f"시작 윈도우({start_w[0]}~{start_w[1]}) 거래 없음", None
    if end_price is None:
        return "no_end", f"종료 윈도우({end_w[0]}~{end_w[1]}) 거래 없음", None
    if (start_tx or 0) < min_tx:
        return "insufficient", f"시작 윈도우 거래 {start_tx}건 (최소 {min_tx}건)", None
    if (end_tx or 0) < min_tx:
        return "insufficient", f"종료 윈도우 거래 {end_tx}건 (최소 {min_tx}건)", None
    if start_price <= 0:
        return "insufficient", "시작 시점 평단가 0 이하", None
    change = round(
        Decimal(str((end_price - start_price) / start_price * 100)), 2
    )
    return "ok", None, change


def compute_complex_rankings(snapshot_ym: str | None = None) -> int:
    """
    지정 기준월 기준으로 전 기간(3m~20y) 단지 랭킹을 계산해 DB에 저장한다.

    Parameters
    ----------
    snapshot_ym : 기준 완성월 (None이면 get_end_ym() 자동 결정)

    Returns
    -------
    int : 저장된 랭킹 레코드 수
    """
    if snapshot_ym is None:
        snapshot_ym = get_end_ym()

    n = settings.re_window_months
    m = settings.re_min_tx_per_window

    logger.info("단지 랭킹 계산 시작: snapshot_ym=%s, N=%d, M=%d", snapshot_ym, n, m)

    with SyncSessionLocal() as session:
        sigungu_name_map = get_sigungu_names_sync(session)

        # 종료 윈도우는 모든 기간이 공유
        end_w: tuple[str, str] = (subtract_months(snapshot_ym, n), snapshot_ym)
        end_df_raw = _load_transactions_window(session, end_w[0], end_w[1])
        end_df = _add_complex_key(end_df_raw) if not end_df_raw.empty else end_df_raw
        end_stats = _compute_window_stats(end_df)
        end_lookup = end_stats.set_index("complex_key") if not end_stats.empty else pd.DataFrame()

        logger.info(
            "종료 윈도우 %s~%s: %d건 거래, %d개 단지",
            end_w[0], end_w[1], len(end_df_raw), len(end_stats),
        )

        total_saved = 0

        for period, months in PERIOD_MONTHS.items():
            start_ym = subtract_months(snapshot_ym, months)
            start_w, _, overlap = _get_windows(period, start_ym, snapshot_ym, n)

            logger.info(
                "period=%s: start_window=%s~%s, end_window=%s~%s%s",
                period, start_w[0], start_w[1], end_w[0], end_w[1],
                " [1개월 겹침]" if overlap else "",
            )

            start_df_raw = _load_transactions_window(session, start_w[0], start_w[1])
            start_df = _add_complex_key(start_df_raw) if not start_df_raw.empty else start_df_raw
            start_stats = _compute_window_stats(start_df)
            start_lookup = (
                start_stats.set_index("complex_key") if not start_stats.empty else pd.DataFrame()
            )

            all_keys = (
                set(start_lookup.index) | set(end_lookup.index)
                if not start_lookup.empty else set(end_lookup.index)
            )

            snapshot_records: list[dict[str, Any]] = []

            for key in all_keys:
                has_start = not start_lookup.empty and key in start_lookup.index
                has_end = not end_lookup.empty and key in end_lookup.index

                # 단지 메타 (종료 우선, 없으면 시작에서)
                src = end_lookup if has_end else start_lookup
                row = src.loc[key]
                sigungu_code = str(row["sigungu_code"])
                eupmyeondong = str(row["eupmyeondong"])
                apt_name = str(row["apt_name"])
                sigungu_name = sigungu_name_map.get(sigungu_code, sigungu_code)
                display_name = _get_complex_display_name(
                    sigungu_code, sigungu_name, eupmyeondong, apt_name
                )

                start_price = float(start_lookup.loc[key, "median_price"]) if has_start else None
                start_deal_amount = float(start_lookup.loc[key, "median_deal_amount"]) if has_start else None
                start_tx = int(start_lookup.loc[key, "tx_count"]) if has_start else None
                end_price = float(end_lookup.loc[key, "median_price"]) if has_end else None
                end_deal_amount = float(end_lookup.loc[key, "median_deal_amount"]) if has_end else None
                end_tx = int(end_lookup.loc[key, "tx_count"]) if has_end else None

                data_status, reason, change_pct = _determine_status(
                    start_price, end_price, start_tx, end_tx, m, start_w, end_w
                )

                snapshot_records.append({
                    "snapshot_ym": snapshot_ym,
                    "period": period,
                    "rank": None,
                    "complex_key": key,
                    "sigungu_code": sigungu_code,
                    "sigungu_name": sigungu_name[:100],
                    "eupmyeondong": eupmyeondong[:100],
                    "apt_name": apt_name[:200],
                    "display_name": display_name[:400],
                    "start_ym": start_ym,
                    "end_ym": snapshot_ym,
                    "start_price": (
                        round(Decimal(str(start_price)), 2) if start_price is not None else None
                    ),
                    "end_price": (
                        round(Decimal(str(end_price)), 2) if end_price is not None else None
                    ),
                    "start_deal_amount": (
                        round(Decimal(str(start_deal_amount))) if start_deal_amount is not None else None
                    ),
                    "end_deal_amount": (
                        round(Decimal(str(end_deal_amount))) if end_deal_amount is not None else None
                    ),
                    "change_pct": change_pct,
                    "start_tx_count": start_tx,
                    "end_tx_count": end_tx,
                    "data_status": data_status,
                    "insufficient_reason": reason,
                    "windows_overlap": overlap,
                })

            # ok 항목 change_pct 내림차순 rank 부여
            ok_records = [r for r in snapshot_records if r["data_status"] == "ok"]
            ok_records.sort(key=lambda r: float(r["change_pct"]), reverse=True)
            for i, r in enumerate(ok_records, start=1):
                r["rank"] = i

            upsert_complex_ranking_snapshots_sync(session, snapshot_records)
            total_saved += len(snapshot_records)

            logger.info(
                "period=%s: ok=%d, excluded=%d, 총 %d개 단지 저장",
                period, len(ok_records),
                len(snapshot_records) - len(ok_records), len(snapshot_records),
            )

    logger.info("단지 랭킹 계산 완료: 총 %d건 저장", total_saved)
    return total_saved

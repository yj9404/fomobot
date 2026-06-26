"""
랭킹 계산 배치.

re_monthly_stat 테이블에서 기간별 평단가 중위값 변화율을 계산해
re_ranking_snapshot에 저장한다.

pandas 벡터 연산으로 처리 (지역 루프 최소화).
API는 re_ranking_snapshot만 읽으므로 실시간 계산 금지.
"""

import logging
from decimal import Decimal
from typing import Any

import pandas as pd

from realestate.batch.regions import SIGUNGU_MAP, get_display_name
from realestate.config import settings
from realestate.db.crud import (
    get_monthly_stats_for_ranking_sync,
    get_sigungu_names_sync,
    upsert_ranking_snapshots_sync,
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


def subtract_months(ym: str, months: int) -> str:
    """YYYYMM에서 months 개월을 뺀 YYYYMM을 반환한다."""
    year = int(ym[:4])
    month = int(ym[4:])
    month -= months
    while month <= 0:
        month += 12
        year -= 1
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


def _build_region_key(sigungu_code: str, eupmyeondong: str | None) -> str:
    return f"{sigungu_code}|{eupmyeondong or ''}"


def compute_rankings(
    snapshot_ym: str | None = None,
    region_level: str = "gu",
) -> int:
    """
    지정 기준월 기준으로 전 기간(3m~20y) 랭킹을 계산해 DB에 저장한다.

    Parameters
    ----------
    snapshot_ym : 기준 완성월 (None이면 get_end_ym() 자동 결정)
    region_level : 'gu' | 'dong'

    Returns
    -------
    int : 저장된 랭킹 레코드 수
    """
    if snapshot_ym is None:
        snapshot_ym = get_end_ym()

    logger.info("랭킹 계산 시작: level=%s, snapshot_ym=%s", region_level, snapshot_ym)

    # 필요한 모든 년월 수집
    all_yms: set[str] = {snapshot_ym}
    for months in PERIOD_MONTHS.values():
        all_yms.add(subtract_months(snapshot_ym, months))

    # re_monthly_stat 로드
    with SyncSessionLocal() as session:
        rows = get_monthly_stats_for_ranking_sync(session, region_level, sorted(all_yms))
        sigungu_name_map = get_sigungu_names_sync(session)

    if not rows:
        logger.warning("랭킹 계산할 데이터 없음 (level=%s)", region_level)
        return 0

    # DataFrame으로 변환
    df = pd.DataFrame(rows)
    df["price"] = pd.to_numeric(df["median_price_per_sqm"], errors="coerce")
    df["tx_count"] = df["transaction_count"].fillna(0).astype(int)
    df["region_key"] = df.apply(
        lambda r: _build_region_key(r["sigungu_code"], r["eupmyeondong"]), axis=1
    )

    total_saved = 0

    with SyncSessionLocal() as session:
        for period_key, months in PERIOD_MONTHS.items():
            start_ym = subtract_months(snapshot_ym, months)
            end_ym = snapshot_ym

            # start_ym과 end_ym에 데이터가 있는 행 추출
            start_df = df[df["deal_ym"] == start_ym].set_index("region_key")
            end_df = df[df["deal_ym"] == end_ym].set_index("region_key")

            all_keys = set(start_df.index) | set(end_df.index)

            snapshot_records: list[dict[str, Any]] = []

            for key in all_keys:
                parts = key.split("|", 1)
                sigungu_code = parts[0]
                eupmyeondong = parts[1] if parts[1] else None

                sg_info = SIGUNGU_MAP.get(sigungu_code, {})
                sigungu_name = sigungu_name_map.get(sigungu_code) or sg_info.get("name", sigungu_code)
                display_name = get_display_name(sigungu_code, sigungu_name, eupmyeondong)

                has_start = key in start_df.index
                has_end = key in end_df.index

                start_price = start_df.loc[key, "price"] if has_start else None
                end_price = end_df.loc[key, "price"] if has_end else None
                start_tx = int(start_df.loc[key, "tx_count"]) if has_start else None
                end_tx = int(end_df.loc[key, "tx_count"]) if has_end else None

                # 데이터 상태 결정
                if not has_start or pd.isna(start_price):
                    data_status = "no_start"
                    reason = f"시작 시점({start_ym}) 거래 데이터 없음"
                    change_pct = None
                elif not has_end or pd.isna(end_price):
                    data_status = "no_end"
                    reason = f"종료 시점({end_ym}) 거래 데이터 없음"
                    change_pct = None
                elif (end_tx or 0) < settings.re_min_transaction_count:
                    data_status = "insufficient"
                    reason = f"거래 건수 부족 ({end_tx}건, 최소 {settings.re_min_transaction_count}건)"
                    change_pct = None
                elif (start_tx or 0) < settings.re_min_transaction_count:
                    data_status = "insufficient"
                    reason = f"시작 시점 거래 건수 부족 ({start_tx}건, 최소 {settings.re_min_transaction_count}건)"
                    change_pct = None
                elif start_price <= 0:
                    data_status = "insufficient"
                    reason = "시작 시점 평단가 0 이하"
                    change_pct = None
                else:
                    data_status = "ok"
                    reason = None
                    change_pct = round(
                        Decimal(str((end_price - start_price) / start_price * 100)), 2
                    )

                snapshot_records.append({
                    "snapshot_ym": snapshot_ym,
                    "region_level": region_level,
                    "period": period_key,
                    "rank": None,  # 아래서 채움
                    "sigungu_code": sigungu_code,
                    "sigungu_name": sigungu_name,
                    "eupmyeondong": eupmyeondong,
                    "display_name": display_name,
                    "start_ym": start_ym,
                    "end_ym": end_ym,
                    "start_price": round(Decimal(str(start_price)), 2) if start_price is not None and not pd.isna(start_price) else None,
                    "end_price": round(Decimal(str(end_price)), 2) if end_price is not None and not pd.isna(end_price) else None,
                    "change_pct": change_pct,
                    "start_tx_count": start_tx,
                    "end_tx_count": end_tx,
                    "data_status": data_status,
                    "insufficient_reason": reason,
                })

            # ok 항목만 change_pct 내림차순으로 rank 부여
            ok_records = [r for r in snapshot_records if r["data_status"] == "ok"]
            ok_records.sort(key=lambda r: float(r["change_pct"]), reverse=True)
            for i, r in enumerate(ok_records, start=1):
                r["rank"] = i

            upsert_ranking_snapshots_sync(session, snapshot_records)
            total_saved += len(snapshot_records)

            ok_count = len(ok_records)
            excl_count = len(snapshot_records) - ok_count
            logger.info(
                "level=%s period=%s: ok=%d 지역, excluded=%d 지역 저장",
                region_level, period_key, ok_count, excl_count,
            )

    logger.info("랭킹 계산 완료: level=%s, 총 %d건 저장", region_level, total_saved)
    return total_saved


def compute_all_rankings(snapshot_ym: str | None = None) -> None:
    """구 단위와 동 단위 랭킹을 모두 계산한다."""
    for level in ("gu", "dong"):
        try:
            compute_rankings(snapshot_ym, level)
        except Exception:
            logger.exception("랭킹 계산 오류 (level=%s)", level)

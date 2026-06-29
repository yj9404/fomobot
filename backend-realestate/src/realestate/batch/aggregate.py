"""
월별 지역 집계 배치.

re_transaction 원천 데이터에서 (시군구, 법정동, 년월) 단위로
㎡당 단가 중위값과 거래 건수를 계산해 re_monthly_stat에 저장한다.

구 단위 (eupmyeondong=None): 시군구 전체 집계
동 단위 (eupmyeondong='xxx'): 법정동 단위 집계
"""

import logging
from decimal import Decimal

import pandas as pd
from sqlalchemy import text

from realestate.db.crud import upsert_monthly_stats_sync
from realestate.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)


def _load_transactions(session, sigungu_code: str, deal_yms: list[str]) -> pd.DataFrame:
    if not deal_yms:
        return pd.DataFrame()
    ym_list = ", ".join(f"'{ym}'" for ym in deal_yms)
    sql = text(f"""
        SELECT eupmyeondong, deal_ym, price_per_sqm
        FROM re_transaction
        WHERE sigungu_code = :code
          AND deal_ym IN ({ym_list})
          AND price_per_sqm > 0
    """)
    result = session.execute(sql, {"code": sigungu_code})
    rows = [dict(r._mapping) for r in result]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["price_per_sqm"] = df["price_per_sqm"].astype(float)
    return df


def aggregate_sigungu(sigungu_code: str, deal_yms: list[str]) -> int:
    """
    지정한 시군구의 년월 목록에 대해 구/동 단위 집계를 계산·저장한다.

    Returns
    -------
    int : 저장된 통계 레코드 수 (구 단위 + 동 단위 합계)
    """
    with SyncSessionLocal() as session:
        df = _load_transactions(session, sigungu_code, deal_yms)

        records: list[dict] = []

        if df.empty:
            # 해당 기간에 거래가 전혀 없는 경우도 "거래 0건" 레코드로 저장
            for ym in deal_yms:
                records.append({
                    "sigungu_code": sigungu_code,
                    "eupmyeondong": None,
                    "deal_ym": ym,
                    "median_price_per_sqm": None,
                    "transaction_count": 0,
                })
        else:
            # ── 구 단위 집계 ────────────────────────────────────────────
            gu_agg = (
                df.groupby("deal_ym")["price_per_sqm"]
                .agg(median="median", count="count")
                .reset_index()
            )
            for row in gu_agg.itertuples(index=False):
                records.append({
                    "sigungu_code": sigungu_code,
                    "eupmyeondong": None,
                    "deal_ym": row.deal_ym,
                    "median_price_per_sqm": round(Decimal(str(row.median)), 2),
                    "transaction_count": int(row.count),
                })

            # 거래 없는 월도 0건으로 기록
            covered_yms = set(gu_agg["deal_ym"].tolist())
            for ym in deal_yms:
                if ym not in covered_yms:
                    records.append({
                        "sigungu_code": sigungu_code,
                        "eupmyeondong": None,
                        "deal_ym": ym,
                        "median_price_per_sqm": None,
                        "transaction_count": 0,
                    })

            # ── 동 단위 집계 ────────────────────────────────────────────
            dong_agg = (
                df.groupby(["eupmyeondong", "deal_ym"])["price_per_sqm"]
                .agg(median="median", count="count")
                .reset_index()
            )
            for row in dong_agg.itertuples(index=False):
                records.append({
                    "sigungu_code": sigungu_code,
                    "eupmyeondong": str(row.eupmyeondong)[:50],
                    "deal_ym": row.deal_ym,
                    "median_price_per_sqm": round(Decimal(str(row.median)), 2),
                    "transaction_count": int(row.count),
                })

        upsert_monthly_stats_sync(session, records)
        logger.info(
            "%s 집계 완료: %d개월, %d건 레코드 저장",
            sigungu_code, len(deal_yms), len(records),
        )
        return len(records)


def aggregate_all_sigungu(deal_yms: list[str]) -> None:
    """수도권 전체 시군구에 대해 집계를 실행한다."""
    from realestate.batch.regions import SUDOGWON_SIGUNGU

    for sg in SUDOGWON_SIGUNGU:
        try:
            aggregate_sigungu(sg["code"], deal_yms)
        except Exception:
            logger.exception("%s 집계 중 오류", sg["code"])

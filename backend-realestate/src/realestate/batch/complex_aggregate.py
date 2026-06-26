"""
단지 월별 집계 배치.

re_transaction 원천 데이터에서 (단지, 년월) 단위로
㎡당 단가 중위값과 거래 건수를 계산해 re_complex_stat에 저장한다.

단지 식별: normalize_apt_name(apt_name) + sigungu_code + eupmyeondong 조합.
랭킹 계산은 re_transaction을 직접 읽으므로 이 테이블은
단지 메타데이터 캐시와 향후 상세 API용으로 사용된다.
"""

import logging
from decimal import Decimal

import pandas as pd
from sqlalchemy import text

from realestate.batch.normalize import make_complex_key, normalize_apt_name
from realestate.db.crud import upsert_complex_stats_sync
from realestate.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)


def _load_transactions(session, sigungu_code: str, deal_yms: list[str]) -> pd.DataFrame:
    if not deal_yms:
        return pd.DataFrame()
    ym_list = ", ".join(f"'{ym}'" for ym in deal_yms)
    sql = text(f"""
        SELECT sigungu_code, eupmyeondong, apt_name, deal_ym, price_per_sqm
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


def aggregate_sigungu_complex(sigungu_code: str, deal_yms: list[str]) -> int:
    """
    지정 시군구의 년월 목록에 대해 단지×월 집계를 계산·저장한다.

    Returns
    -------
    int : 저장된 레코드 수
    """
    with SyncSessionLocal() as session:
        df = _load_transactions(session, sigungu_code, deal_yms)
        if df.empty:
            logger.info("%s: 해당 기간 거래 없음", sigungu_code)
            return 0

        df["apt_name_norm"] = df["apt_name"].apply(normalize_apt_name)
        df["complex_key"] = df.apply(
            lambda r: make_complex_key(r["sigungu_code"], r["eupmyeondong"], r["apt_name_norm"]),
            axis=1,
        )

        # 단지별 가장 최근 표기를 표시명으로 사용
        meta_df = (
            df.groupby("complex_key")[["eupmyeondong", "apt_name", "apt_name_norm"]]
            .last()
        )

        # (complex_key, deal_ym) 단위 중위값·건수 집계
        agg = (
            df.groupby(["complex_key", "sigungu_code", "deal_ym"])["price_per_sqm"]
            .agg(median="median", count="count")
            .reset_index()
        )

        records: list[dict] = []
        for _, row in agg.iterrows():
            key = row["complex_key"]
            meta = meta_df.loc[key]
            records.append({
                "complex_key": key,
                "sigungu_code": row["sigungu_code"],
                "eupmyeondong": str(meta["eupmyeondong"])[:100],
                "apt_name": str(meta["apt_name"])[:200],
                "apt_name_norm": str(meta["apt_name_norm"])[:200],
                "deal_ym": row["deal_ym"],
                "median_price_per_sqm": round(Decimal(str(row["median"])), 2),
                "transaction_count": int(row["count"]),
            })

        upsert_complex_stats_sync(session, records)
        logger.info(
            "%s 단지 집계 완료: %d개월, 단지×월 %d건 저장",
            sigungu_code, len(deal_yms), len(records),
        )
        return len(records)


def aggregate_all_sigungu_complex(deal_yms: list[str]) -> None:
    """수도권 전체 시군구에 대해 단지 집계를 실행한다."""
    from realestate.batch.regions import SUDOGWON_SIGUNGU

    for sg in SUDOGWON_SIGUNGU:
        try:
            aggregate_sigungu_complex(sg["code"], deal_yms)
        except Exception:
            logger.exception("%s 단지 집계 중 오류", sg["code"])

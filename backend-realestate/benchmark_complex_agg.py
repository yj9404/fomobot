import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from unittest.mock import patch
import pandas as pd
from decimal import Decimal
import logging

from realestate.batch.complex_aggregate import aggregate_all_sigungu_complex, _load_transactions
from realestate.batch.regions import SUDOGWON_SIGUNGU
import realestate.batch.complex_aggregate as ca
from realestate.batch.normalize import make_complex_key, normalize_apt_name

# Create SQLite engine and schema
engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE re_transaction (
            sigungu_code VARCHAR,
            eupmyeondong VARCHAR,
            apt_name VARCHAR,
            deal_ym VARCHAR,
            price_per_sqm FLOAT,
            deal_date VARCHAR
        )
    """))
    # Insert data for each sigungu
    for sg in SUDOGWON_SIGUNGU:
        code = sg["code"]
        for i in range(100):
            conn.execute(text(f"""
                INSERT INTO re_transaction (sigungu_code, eupmyeondong, apt_name, deal_ym, price_per_sqm, deal_date)
                VALUES ('{code}', '동{i}', '아파트{i}', '202310', 1000.0, '20231001')
            """))
    conn.commit()

@patch('realestate.batch.complex_aggregate.SyncSessionLocal', SessionLocal)
@patch('realestate.batch.complex_aggregate.upsert_complex_stats_sync')
def run_baseline(mock_upsert):
    start = time.time()
    aggregate_all_sigungu_complex(["202310"])
    return time.time() - start

def aggregate_all_sigungu_complex_optimized(deal_yms: list[str]) -> None:
    if not deal_yms:
        return
    with SessionLocal() as session:
        ym_list = ", ".join(f"'{ym}'" for ym in deal_yms)
        sql = text(f"""
            SELECT sigungu_code, eupmyeondong, apt_name, deal_ym, price_per_sqm
            FROM re_transaction
            WHERE deal_ym IN ({ym_list})
              AND price_per_sqm > 0
        """)
        result = session.execute(sql)
        rows = [dict(r._mapping) for r in result]
        if not rows:
            return

        df = pd.DataFrame(rows)
        df["price_per_sqm"] = df["price_per_sqm"].astype(float)

        df["apt_name_norm"] = df["apt_name"].apply(normalize_apt_name)
        df["complex_key"] = df.apply(
            lambda r: make_complex_key(
                r["sigungu_code"], r["eupmyeondong"], r["apt_name_norm"]
            ),
            axis=1,
        )

        # 단지별 가장 최근 표기를 표시명으로 사용
        meta_df = df.groupby("complex_key")[
            ["eupmyeondong", "apt_name", "apt_name_norm"]
        ].last()

        # (complex_key, deal_ym) 단위 중위값·건수 집계
        agg = (
            df.groupby(["complex_key", "sigungu_code", "deal_ym"])["price_per_sqm"]
            .agg(median="median", tx_count="count")
            .reset_index()
        )

        meta_dict = meta_df.to_dict("index")

        records: list[dict] = []
        for row in agg.itertuples(index=False):
            key = row.complex_key
            meta = meta_dict[key]
            records.append(
                {
                    "complex_key": key,
                    "sigungu_code": row.sigungu_code,
                    "eupmyeondong": str(meta["eupmyeondong"])[:100],
                    "apt_name": str(meta["apt_name"])[:200],
                    "apt_name_norm": str(meta["apt_name_norm"])[:200],
                    "deal_ym": row.deal_ym,
                    "median_price_per_sqm": round(Decimal(str(row.median)), 2),
                    "transaction_count": int(row.tx_count),
                }
            )

        ca.upsert_complex_stats_sync(session, records)

@patch('realestate.batch.complex_aggregate.upsert_complex_stats_sync')
def run_optimized(mock_upsert):
    start = time.time()
    aggregate_all_sigungu_complex_optimized(["202310"])
    return time.time() - start


print("Baseline:", run_baseline())
print("Optimized:", run_optimized())

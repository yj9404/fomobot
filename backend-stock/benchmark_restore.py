import asyncio
import time
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Set env vars for DB
os.environ["DATABASE_URL"] = "postgresql://fomobot:fomobot@localhost:5433/fomobot_re"
os.environ["KRX_ID"] = "dummy"

# Add backend-stock/src to path
sys.path.insert(0, os.path.abspath("src"))

from scripts.restore_history import restore_nasdaq, get_conn
import pandas as pd
import datetime

upsert_calls = 0
total_records_upserted = 0

async def mock_upsert_price_daily(conn, records):
    global upsert_calls, total_records_upserted
    upsert_calls += 1
    total_records_upserted += len(records)
    # simulate db latency: 10ms network roundtrip + insert cost
    await asyncio.sleep(0.01)
    return len(records)

async def run_bench():
    with patch("scripts.restore_history.get_covered_tickers", new_callable=AsyncMock) as m_covered, \
         patch("fomobot.batch.collect_nasdaq.fetch_nasdaq_tickers") as m_fetch, \
         patch("fomobot.batch.collect_nasdaq._fetch_nasdaq_name_map") as m_name_map, \
         patch("fomobot.batch.collect_nasdaq._download_batch") as m_download, \
         patch("fomobot.batch.collect_nasdaq._parse_batch_df") as m_parse, \
         patch("scripts.restore_history.upsert_price_daily", new=mock_upsert_price_daily), \
         patch("scripts.restore_history.upsert_index_daily", new_callable=AsyncMock) as m_idx, \
         patch("scripts.restore_history.upsert_securities_master", new_callable=AsyncMock) as m_sec, \
         patch("scripts.restore_history.get_conn", new_callable=AsyncMock) as m_conn, \
         patch("time.sleep", return_value=None):

        m_covered.return_value = set()
        m_fetch.return_value = [f"TICK{i}" for i in range(7000)] # 70 batches of 100
        m_name_map.return_value = {}

        m_download.return_value = pd.DataFrame()
        def side_effect_parse(df, batch, market):
            # 25 records per ticker
            return [{"ticker": t, "market": "nasdaq", "date": datetime.date.today(), "close_adj": 100.0} for t in batch * 25]
        m_parse.side_effect = side_effect_parse

        m_conn.return_value = AsyncMock()

        global upsert_calls, total_records_upserted
        upsert_calls = 0
        total_records_upserted = 0

        start_time = time.time()
        await restore_nasdaq()
        end_time = time.time()
        print(f"Elapsed: {end_time - start_time:.4f} seconds")
        print(f"Upsert calls: {upsert_calls}")
        print(f"Total upserted: {total_records_upserted}")

asyncio.run(run_bench())

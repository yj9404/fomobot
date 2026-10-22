import asyncio
import time
import os
import sys
from unittest.mock import patch, MagicMock

# Set env vars for DB
os.environ["DATABASE_URL"] = "postgresql://fomobot:fomobot@localhost:5433/fomobot_re"

# Add backend-stock/src to path
sys.path.insert(0, os.path.abspath("backend-stock/src"))
sys.path.insert(0, os.path.abspath("backend-stock"))

from scripts.restore_history import restore_nasdaq, get_conn
import pandas as pd
import datetime

async def mock_upsert_price_daily(conn, records):
    # simulate db latency
    await asyncio.sleep(0.01)
    return len(records)

async def run_bench():
    # Mock get_covered_tickers, fetch_nasdaq_tickers, _download_batch, _parse_batch_df, _fetch_nasdaq_name_map
    with patch("scripts.restore_history.get_covered_tickers", new_callable=MagicMock) as m_covered, \
         patch("fomobot.batch.collect_nasdaq.fetch_nasdaq_tickers") as m_fetch, \
         patch("fomobot.batch.collect_nasdaq._fetch_nasdaq_name_map") as m_name_map, \
         patch("fomobot.batch.collect_nasdaq._download_batch") as m_download, \
         patch("fomobot.batch.collect_nasdaq._parse_batch_df") as m_parse, \
         patch("scripts.restore_history.upsert_price_daily", new=mock_upsert_price_daily), \
         patch("scripts.restore_history.get_conn") as m_conn, \
         patch("time.sleep", return_value=None):

        m_covered.return_value = set()
        # Generate 1000 tickers to make 10 batches
        m_fetch.return_value = [f"TICK{i}" for i in range(1000)]
        m_name_map.return_value = {}

        # mock return dataframe and parsed records
        m_download.return_value = pd.DataFrame()
        # Each batch gives 10,000 records
        def side_effect_parse(df, batch, market):
            return [{"ticker": t, "market": "nasdaq", "date": datetime.date.today(), "close_adj": 100.0} for t in batch * 100]
        m_parse.side_effect = side_effect_parse

        m_conn.return_value = MagicMock()
        m_conn.return_value.close = MagicMock()

        start_time = time.time()
        await restore_nasdaq()
        end_time = time.time()
        print(f"Elapsed: {end_time - start_time:.4f} seconds")

asyncio.run(run_bench())

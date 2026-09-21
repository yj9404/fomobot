import asyncio
import time
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

os.environ["DATABASE_URL"] = "postgresql://fomobot:fomobot@localhost:5433/fomobot_re"
os.environ["KRX_ID"] = "dummy"

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
        m_fetch.return_value = [f"TICK{i}" for i in range(7000)]
        m_name_map.return_value = {}

        m_download.return_value = pd.DataFrame()
        def side_effect_parse(df, batch, market):
            return [{"ticker": t, "market": "nasdaq", "date": datetime.date.today(), "close_adj": 100.0} for t in batch * 25]
        m_parse.side_effect = side_effect_parse

        m_conn.return_value = AsyncMock()

        global upsert_calls, total_records_upserted
        upsert_calls = 0
        total_records_upserted = 0

        # Patch restore_nasdaq to use accumulated records
        import scripts.restore_history as rh
        original_restore_nasdaq = rh.restore_nasdaq

        async def optimized_restore_nasdaq():
            from fomobot.batch.collect_nasdaq import (
                fetch_nasdaq_tickers,
                _download_batch,
                _parse_batch_df,
                _fetch_nasdaq_name_map,
            )
            from fomobot.config import settings
            start_str = rh.HISTORY_START.strftime("%Y-%m-%d")
            end_str = (rh.HISTORY_END + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            conn = await rh.get_conn()
            try:
                covered = await rh.get_covered_tickers(conn, "nasdaq", rh.HISTORY_START, rh.HISTORY_END)
                all_tickers = fetch_nasdaq_tickers()
                name_map = _fetch_nasdaq_name_map()
                tickers = [t for t in all_tickers if t not in covered]

                batch_size = settings.batch_size_nasdaq
                batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
                consecutive_failures = 0
                total_saved = 0

                price_records = []
                for idx, batch in enumerate(batches):
                    if consecutive_failures >= settings.nasdaq_max_consec_failures:
                        consecutive_failures = 0
                    try:
                        df = _download_batch(batch, start_str, end_str)
                        records = _parse_batch_df(df, batch, "nasdaq")
                        if records:
                            price_records.extend(records)
                        consecutive_failures = 0
                    except Exception:
                        consecutive_failures += 1
                        continue

                    if len(price_records) >= 50_000:
                        saved = await mock_upsert_price_daily(conn, price_records)
                        total_saved += saved
                        price_records.clear()

                if price_records:
                    saved = await mock_upsert_price_daily(conn, price_records)
                    total_saved += saved
                    price_records.clear()
            finally:
                pass

        rh.restore_nasdaq = optimized_restore_nasdaq

        start_time = time.time()
        await rh.restore_nasdaq()
        end_time = time.time()
        print(f"Accumulated Elapsed: {end_time - start_time:.4f} seconds")
        print(f"Upsert calls: {upsert_calls}")
        print(f"Total upserted: {total_records_upserted}")

        rh.restore_nasdaq = original_restore_nasdaq

asyncio.run(run_bench())

import asyncio
import time
from unittest.mock import MagicMock
from datetime import date
from fomobot.api.backtest import backtest_endpoint
from fomobot.schemas.rankings import MarketLiteral, PeriodLiteral
from unittest.mock import patch
import sys

async def run_benchmark():
    class MockRow:
        def __init__(self, ticker):
            self.ticker = ticker
            self.name = f"Name {ticker}"
            self.rank = 1
            self.return_pct = 10.0

    snapshot_rows = [MockRow(f"TICKER_{i}") for i in range(50)]

    # We will just patch `get_nearest_snapshot_date`, `get_rankings`, `_resolve_start_date`
    # and we want to see how many times `get_price_series_async` is called.
    # We don't even need to mock everything if we do a real DB call, but since we are
    # establishing a baseline, we can just use MagicMock for DB dependencies.

    session = MagicMock()

    async def mock_get_nearest(*args): return date(2023, 1, 1)
    async def mock_get_rankings(*args): return snapshot_rows
    async def mock_resolve_start(*args): return date(2022, 1, 1)
    async def mock_get_price_series(*args):
        # simulate some delay
        await asyncio.sleep(0.001)
        return [(date(2022, 1, 1), 10.0), (date(2023, 1, 1), 20.0)]

    async def mock_get_price_series_multi(*args):
        await asyncio.sleep(0.005)
        return {r.ticker: [(date(2022, 1, 1), 10.0), (date(2023, 1, 1), 20.0)] for r in snapshot_rows}

    with patch("fomobot.api.backtest.get_nearest_snapshot_date", side_effect=mock_get_nearest), \
         patch("fomobot.api.backtest.get_rankings", side_effect=mock_get_rankings), \
         patch("fomobot.api.backtest._resolve_start_date", side_effect=mock_resolve_start), \
         patch("fomobot.api.backtest.get_price_series_async", side_effect=mock_get_price_series), \
         patch("fomobot.api.backtest.get_price_series_multi_async", side_effect=mock_get_price_series_multi, create=True):

        start = time.time()
        for _ in range(10):
            await backtest_endpoint(
                market="kospi",
                as_of=date(2023, 1, 1),
                period="30d",
                top=50,
                session=session
            )
        end = time.time()
        print(f"Baseline Time (10 runs, 50 top items): {(end - start):.3f}s")

if __name__ == "__main__":
    asyncio.run(run_benchmark())

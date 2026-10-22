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

    session = MagicMock()

    async def mock_get_nearest(*args): return date(2023, 1, 1)
    async def mock_get_rankings(*args): return snapshot_rows
    async def mock_resolve_start(*args): return date(2022, 1, 1)
    async def mock_get_price_series(*args):
        # simulate some DB latency for a single query
        await asyncio.sleep(0.001)
        return [(date(2022, 1, 1), 10.0), (date(2023, 1, 1), 20.0)]

    async def mock_get_price_series_multi(*args):
        # simulate some DB latency for a multi query (it takes longer than 1 query, but faster than 50 queries)
        await asyncio.sleep(0.005)
        return {r.ticker: [(date(2022, 1, 1), 10.0), (date(2023, 1, 1), 20.0)] for r in snapshot_rows}

    # First, run with N+1 queries.
    with patch("fomobot.api.backtest.get_nearest_snapshot_date", side_effect=mock_get_nearest), \
         patch("fomobot.api.backtest.get_rankings", side_effect=mock_get_rankings), \
         patch("fomobot.api.backtest._resolve_start_date", side_effect=mock_resolve_start), \
         patch("fomobot.api.backtest.get_price_series_async", side_effect=mock_get_price_series), \
         patch("fomobot.api.backtest.get_price_series_multi_async", side_effect=mock_get_price_series_multi, create=True):

        # Backup the actual endpoint implementation
        import fomobot.api.backtest as btest

        async def old_backtest_endpoint_logic(market, as_of, period, top, session):
            actual_date = await btest.get_nearest_snapshot_date(session, market, period, as_of)
            snapshot_rows = await btest.get_rankings(session, market, period, top, actual_date)
            start_date = await btest._resolve_start_date(session, market, period, actual_date)

            items = []
            valid_returns = []
            for row in snapshot_rows:
                # OLD N+1
                price_rows = await btest.get_price_series_async(
                    session, market, row.ticker, start_date, actual_date
                )
                bh = btest._compute_buy_and_hold(price_rows)
                dca = btest._compute_dca(price_rows, period, start_date, actual_date)

                if bh is not None:
                    valid_returns.append(bh.final_return_pct)

            return btest.BacktestResponse(
                market=market,
                period=period,
                as_of=as_of,
                actual_as_of=actual_date,
                top=top,
                avg_buy_and_hold_return_pct=None,
                items=[]
            )

        start = time.time()
        for _ in range(10):
            await old_backtest_endpoint_logic(
                market="kospi",
                as_of=date(2023, 1, 1),
                period="30d",
                top=50,
                session=session
            )
        end = time.time()
        old_time = end - start
        print(f"Old baseline Time (N+1 queries) (10 runs, 50 top items): {old_time:.3f}s")

        # New
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
        new_time = end - start
        print(f"New Time (Batch query) (10 runs, 50 top items): {new_time:.3f}s")
        print(f"Improvement: {old_time/new_time:.2f}x faster")

if __name__ == "__main__":
    asyncio.run(run_benchmark())

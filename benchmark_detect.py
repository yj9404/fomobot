import time
import pandas as pd
from datetime import date, timedelta
from fomobot.batch.detect_corporate_actions import detect_corporate_actions

# Mocking the DB functions
from unittest.mock import patch

def mock_get_price_range_sync(session, market, start_date, end_date):
    # generate a large mock dataset
    data = []
    tickers = [f"TICKER{i}" for i in range(2000)]
    curr_date = start_date
    dates = []
    while curr_date <= end_date:
        dates.append(curr_date)
        curr_date += timedelta(days=1)

    for ticker in tickers:
        for d in dates:
            data.append({
                "ticker": ticker,
                "date": d,
                "close_adj": 1000.0,
                "volume": 1000,
                "market_cap": 1000000.0,
            })
    return data

@patch('fomobot.batch.detect_corporate_actions.SyncSessionLocal')
@patch('fomobot.batch.detect_corporate_actions.get_price_range_sync', side_effect=mock_get_price_range_sync)
@patch('fomobot.batch.detect_corporate_actions.get_resolved_flags_sync', return_value={})
def run_benchmark(mock_resolved, mock_price, mock_session):
    start = time.time()
    res = detect_corporate_actions("kospi", 20, suppress_resolved=False)
    end = time.time()
    print(f"Execution time: {end - start:.4f} seconds")
    print(f"Checked tickers: {res['checked_ticker_count']}")

if __name__ == "__main__":
    run_benchmark()

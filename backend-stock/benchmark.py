import asyncio
from datetime import date
from time import perf_counter
from src.fomobot.api.backtest import _compute_buy_and_hold, _compute_dca

def benchmark():
    # Generate some identical price_rows
    # Imagine 100 tickers, 50 of them have the same price_rows
    price_rows_1 = [(date(2023, 1, i), 100.0 + i) for i in range(1, 28)]
    price_rows_2 = []
    price_rows_3 = [(date(2023, 1, i), 200.0 - i) for i in range(1, 28)]

    all_rows = [price_rows_1] * 40 + [price_rows_2] * 40 + [price_rows_3] * 20

    start_date = date(2023, 1, 1)
    actual_date = date(2023, 1, 27)
    period = "30d"

    # Baseline
    t0 = perf_counter()
    for rows in all_rows:
        _compute_buy_and_hold(rows)
        _compute_dca(rows, period, start_date, actual_date)
    t1 = perf_counter()
    print(f"Baseline: {t1 - t0:.4f}s")

    # Cached
    t2 = perf_counter()
    bh_cache = {}
    dca_cache = {}
    for rows in all_rows:
        # Convert to tuple for hashing
        key = tuple(rows)
        if key not in bh_cache:
            bh_cache[key] = _compute_buy_and_hold(rows)
        if key not in dca_cache:
            dca_cache[key] = _compute_dca(rows, period, start_date, actual_date)
    t3 = perf_counter()
    print(f"Cached: {t3 - t2:.4f}s")

if __name__ == "__main__":
    benchmark()

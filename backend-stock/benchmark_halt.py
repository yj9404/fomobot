import time
from datetime import date
from unittest.mock import MagicMock
import pytest

from fomobot.services.halt_resumption import is_prev_day_halt_resumption, get_prev_day_halt_resumptions

def bench_baseline(monkeypatch):
    session = MagicMock()

    mock_get_price = MagicMock(return_value=[])
    mock_get_flag = MagicMock(return_value=None)

    monkeypatch.setattr("fomobot.services.halt_resumption.get_price_series_for_tickers_sync", mock_get_price)
    monkeypatch.setattr("fomobot.services.halt_resumption.get_corporate_action_flag_sync", mock_get_flag)

    tickers = [f"TICK{i}" for i in range(100)]
    start_date = date(2023, 1, 1)
    snapshot_date = date(2023, 1, 2)

    start_time = time.time()
    for t in tickers:
        is_prev_day_halt_resumption(session, "nasdaq", t, start_date, snapshot_date)
    duration = time.time() - start_time

    return duration, mock_get_price.call_count, mock_get_flag.call_count

def bench_optimized(monkeypatch):
    session = MagicMock()

    mock_get_price_bulk = MagicMock(return_value=[])
    mock_get_flag_bulk = MagicMock(return_value={})

    monkeypatch.setattr("fomobot.services.halt_resumption.get_price_series_for_tickers_sync", mock_get_price_bulk)
    monkeypatch.setattr("fomobot.services.halt_resumption.get_corporate_action_flags_sync", mock_get_flag_bulk)

    tickers = [f"TICK{i}" for i in range(100)]
    start_date = date(2023, 1, 1)
    snapshot_date = date(2023, 1, 2)

    start_time = time.time()
    get_prev_day_halt_resumptions(session, "nasdaq", tickers, start_date, snapshot_date)
    duration = time.time() - start_time

    return duration, mock_get_price_bulk.call_count, mock_get_flag_bulk.call_count

def test_benchmark(monkeypatch):
    baseline_duration, baseline_price, baseline_flag = bench_baseline(monkeypatch)
    opt_duration, opt_price, opt_flag = bench_optimized(monkeypatch)

    print(f"\\nBaseline - N+1 calls: {baseline_price} price queries, {baseline_flag} flag queries, time: {baseline_duration:.4f}s")
    print(f"Optimized - Bulk calls: {opt_price} price queries, {opt_flag} flag queries, time: {opt_duration:.4f}s")

    speedup = baseline_duration / opt_duration if opt_duration > 0 else float('inf')
    print(f"Improvement: Queries reduced from {baseline_price + baseline_flag} to {opt_price + opt_flag}. Speedup: {speedup:.2f}x")

if __name__ == "__main__":
    pytest.main(["-s", "benchmark_halt.py"])

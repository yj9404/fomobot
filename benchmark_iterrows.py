import pandas as pd
import numpy as np
import time

def append_ticker_records_iterrows(records, sub, ticker, market):
    for idx_date, row in sub.iterrows():
        close_val = row.get("Close")
        if pd.isna(close_val):
            continue
        records.append({
            "ticker": ticker,
            "market": market,
            "date": idx_date.date() if hasattr(idx_date, "date") else idx_date,
            "open": float(row["Open"]) if pd.notna(row.get("Open")) else None,
            "high": float(row["High"]) if pd.notna(row.get("High")) else None,
            "low": float(row["Low"]) if pd.notna(row.get("Low")) else None,
            "close_adj": float(close_val),
            "volume": int(row["Volume"]) if pd.notna(row.get("Volume")) else None,
            "market_cap": None,
        })

def append_ticker_records_itertuples(records, sub, ticker, market):
    # Using itertuples
    # Index is named Index
    # the other columns are named Open, High, Low, Close, Volume
    for row in sub.itertuples():
        close_val = getattr(row, "Close", np.nan)
        if pd.isna(close_val):
            continue

        # safely access other attributes
        open_val = getattr(row, "Open", np.nan)
        high_val = getattr(row, "High", np.nan)
        low_val = getattr(row, "Low", np.nan)
        vol_val = getattr(row, "Volume", np.nan)

        idx_date = row.Index

        records.append({
            "ticker": ticker,
            "market": market,
            "date": idx_date.date() if hasattr(idx_date, "date") else idx_date,
            "open": float(open_val) if pd.notna(open_val) else None,
            "high": float(high_val) if pd.notna(high_val) else None,
            "low": float(low_val) if pd.notna(low_val) else None,
            "close_adj": float(close_val),
            "volume": int(vol_val) if pd.notna(vol_val) else None,
            "market_cap": None,
        })

# Setup test data
dates = pd.date_range("2020-01-01", periods=10000)
df = pd.DataFrame({
    "Open": np.random.rand(10000) * 100,
    "High": np.random.rand(10000) * 110,
    "Low": np.random.rand(10000) * 90,
    "Close": np.random.rand(10000) * 105,
    "Volume": np.random.randint(100, 10000, 10000)
}, index=dates)

# introduce some nans
df.loc[df.sample(500).index, "Close"] = np.nan
df.loc[df.sample(500).index, "Open"] = np.nan

ticker = "AAPL"
market = "nasdaq"

records1 = []
t0 = time.time()
append_ticker_records_iterrows(records1, df, ticker, market)
t1 = time.time()
time_iterrows = t1 - t0

records2 = []
t0 = time.time()
append_ticker_records_itertuples(records2, df, ticker, market)
t1 = time.time()
time_itertuples = t1 - t0

print(f"iterrows time: {time_iterrows:.5f}s")
print(f"itertuples time: {time_itertuples:.5f}s")
print(f"Speedup: {time_iterrows / time_itertuples:.2f}x")

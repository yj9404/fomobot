import pandas as pd
import time
from decimal import Decimal

# Dummy data
df = pd.DataFrame({
    "apt_name": ["A파트"] * 10000,
    "dong_name": ["B동"] * 10000,
    "amount": ["50,000"] * 10000,
    "area": ["84.5"] * 10000,
    "day": ["15"] * 10000,
    "floor": ["5"] * 10000,
    "build": ["2010"] * 10000,
})

def _parse_amount(val) -> int | None:
    if pd.isna(val):
        return None
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None

def _parse_decimal(val):
    if pd.isna(val):
        return None
    try:
        return Decimal(str(val).strip())
    except Exception:
        return None

def _parse_int(val):
    if pd.isna(val):
        return None
    try:
        return int(str(val).strip())
    except Exception:
        return None

def process_iterrows(df):
    records = []
    apt_col = "apt_name"
    dong_col = "dong_name"
    amount_col = "amount"
    area_col = "area"
    day_col = "day"
    floor_col = "floor"
    build_col = "build"

    start = time.time()
    for _, row in df.iterrows():
        apt_name = str(row[apt_col]).strip()[:100] if apt_col else ""
        eupmyeondong = str(row[dong_col]).strip()[:50] if dong_col else ""
        deal_amount = _parse_amount(row[amount_col])
        exclusive_area = _parse_decimal(row[area_col])
        deal_day = _parse_int(row[day_col])
        floor = _parse_int(row[floor_col]) if floor_col else None
        build_year = _parse_int(row[build_col]) if build_col else None

        records.append((apt_name, eupmyeondong, deal_amount, exclusive_area, deal_day, floor, build_year))
    end = time.time()
    return end - start

def process_itertuples(df):
    records = []
    apt_col = "apt_name"
    dong_col = "dong_name"
    amount_col = "amount"
    area_col = "area"
    day_col = "day"
    floor_col = "floor"
    build_col = "build"

    col_list = list(df.columns)
    apt_idx = col_list.index(apt_col) if apt_col else None
    dong_idx = col_list.index(dong_col) if dong_col else None
    amount_idx = col_list.index(amount_col)
    area_idx = col_list.index(area_col)
    day_idx = col_list.index(day_col)
    floor_idx = col_list.index(floor_col) if floor_col else None
    build_idx = col_list.index(build_col) if build_col else None

    start = time.time()
    for row in df.itertuples(index=False, name=None):
        apt_name = str(row[apt_idx]).strip()[:100] if apt_col else ""
        eupmyeondong = str(row[dong_idx]).strip()[:50] if dong_col else ""
        deal_amount = _parse_amount(row[amount_idx])
        exclusive_area = _parse_decimal(row[area_idx])
        deal_day = _parse_int(row[day_idx])
        floor = _parse_int(row[floor_idx]) if floor_col else None
        build_year = _parse_int(row[build_idx]) if build_col else None

        records.append((apt_name, eupmyeondong, deal_amount, exclusive_area, deal_day, floor, build_year))
    end = time.time()
    return end - start

t1 = process_iterrows(df)
t2 = process_itertuples(df)

print(f"iterrows:   {t1:.4f} seconds")
print(f"itertuples: {t2:.4f} seconds")
print(f"Speedup:    {t1/t2:.2f}x")

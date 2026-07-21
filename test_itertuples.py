import pandas as pd
import time

def clean_df_old(df, apt_col, amount_col):
    records = []
    for _, row in df.iterrows():
        apt_name = str(row[apt_col])
        amount = int(row[amount_col])
        records.append((apt_name, amount))
    return records

def clean_df_new(df, apt_col, amount_col):
    records = []
    apt_idx = df.columns.get_loc(apt_col)
    amount_idx = df.columns.get_loc(amount_col)
    for row in df.itertuples(index=False, name=None):
        apt_name = str(row[apt_idx])
        amount = int(row[amount_idx])
        records.append((apt_name, amount))
    return records

df = pd.DataFrame({
    "아파트 이름": ["A파트"] * 10000,
    "거래금액": [50000] * 10000
})

start = time.time()
clean_df_old(df, "아파트 이름", "거래금액")
print("old:", time.time() - start)

start = time.time()
clean_df_new(df, "아파트 이름", "거래금액")
print("new:", time.time() - start)

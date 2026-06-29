import pandas as pd
df = pd.DataFrame({"Symbol": ["A", "B"], "Security Name": ["A Inc", "B Inc"]})
name_col = "Security Name"
sym_idx = df.columns.get_loc("Symbol")
name_idx = df.columns.get_loc(name_col)
ticker_set = {"A"}
name_map = {}
for row in df.itertuples(index=False, name=None):
    sym = str(row[sym_idx]).strip()
    if sym in ticker_set:
        name_map[sym] = str(row[name_idx]).strip()[:200]
print(name_map)

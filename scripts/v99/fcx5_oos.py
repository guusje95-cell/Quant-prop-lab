"""F-CX5 diagnostic (0 trials): the basket members were selected on 2022-24, so only 2025-26 is out of sample for them.
Book by year and 2025-01..2026-09 Sharpe, futures + CX4 with vs without CXB. Writes results/v99/fcx5_oos.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/gen137_cme_crypto.py").read_text().split("rows, keep = [], {}")[0]
g = {"__file__": str(ROOT / "scripts/gen137_cme_crypto.py"), "__name__": "gen137"}
exec(src, g)
import basket_live as BL
import futures_db as F
from qpl.live import futures_cx as FX

P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
P["CX"] = pd.read_parquet(FX.PREFIX)["CX"].add(pd.read_parquet(FX.PREFIX4)["legs"], fill_value=0.0).reindex(P.index).fillna(0.0)
_, W = BL.basket(pd.date_range("2019-06-01", "2026-09-30 23:00", freq="h"))
bw = sum(w.reindex(columns=["BTC", "ETH"]).fillna(0.0) for w in W.values())
P2 = P.copy(); P2["CXB"] = FX.daily(g["execute"](g["d2h"](bw), "a")).reindex(P.index).fillna(0.0)
yr = lambda b: {str(y): round(float(b[b.index.year == y].mean() / b[b.index.year == y].std() * np.sqrt(252)), 2) for y in range(2019, 2027)}
b0, b1 = FX.book(P)[0], FX.book(P2)[0]
out = {"book by year, futures + CX4": yr(b0), "book by year, + CXB": yr(b1),
       "2025-01..2026-09 (out of sample for the members)": [round(F.sharpe(b0, "2025-01-01", "2026-09-30"), 3), round(F.sharpe(b1, "2025-01-01", "2026-09-30"), 3)],
       "CXB sleeve 2025-26": round(F.sharpe(P2["CXB"], "2025-01-01", "2026-09-30"), 3)}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/fcx5_oos.json").write_text(json.dumps(out, indent=1))

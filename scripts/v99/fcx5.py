"""F-CX5 (research/v99/fcx5_protocol.json). Writes results/v99/fcx5.json."""
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

per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
P["CX"] = pd.read_parquet(FX.PREFIX)["CX"].add(pd.read_parquet(FX.PREFIX4)["legs"], fill_value=0.0).reindex(P.index).fillna(0.0)
_, W = BL.basket(pd.date_range("2019-06-01", "2026-09-30 23:00", freq="h"))
bw = sum(w.reindex(columns=["BTC", "ETH"]).fillna(0.0) for w in W.values())
out = {"reference (futures + CX4)": per(FX.book(P)[0])}
for name, m in (("with CXB", 1.0), ("with CXB at 2x CME costs", 2.0)):
    orig = F.cost_frac; F.cost_frac = lambda c, px, m=m: m * orig(c, px)
    h = g["execute"](g["d2h"](bw), "a"); F.cost_frac = orig
    P2 = P.copy(); P2["CXB"] = FX.daily(h).reindex(P.index).fillna(0.0)
    out[name] = per(FX.book(P2)[0]); out[name + " sleeve"] = per(P2["CXB"])
    if m == 1.0:
        s = P2["CXB"]; out["CXB by year"] = {str(y): round(float(s[s.index.year == y].mean() / s[s.index.year == y].std() * np.sqrt(252)), 2) for y in range(2019, 2027) if s[s.index.year == y].std() > 0}
        out["corr CXB vs CX4"] = round(float(P2.loc["2020":, "CXB"].corr(P2.loc["2020":, "CX"])), 3)
out["pass"] = bool(out["with CXB"][2] >= 1.615 and out["with CXB"][1] >= 1.679 and out["with CXB at 2x CME costs"][2] >= 1.615)
print(json.dumps(out, indent=1)); (ROOT / "results/v99/fcx5.json").write_text(json.dumps(out, indent=1))

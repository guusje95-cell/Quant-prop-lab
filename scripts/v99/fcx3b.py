"""F-CX3b robustness (research/v99/fcx3b_protocol.json). Writes results/v99/fcx3b.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/gen137_cme_crypto.py").read_text().split("rows, keep = [], {}")[0]
g = {"__file__": str(ROOT / "scripts/gen137_cme_crypto.py"), "__name__": "gen137"}
exec(src, g)
k = {"__file__": str(ROOT / "scripts/gen105_demand.py"), "__name__": "gen105"}
exec((ROOT / "scripts/gen105_demand.py").read_text().split("idx1 = IDX.append")[0], k)
import futures_db as F
from qpl.live.futures_cx import book, daily

per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
yr = lambda b: {str(y): round(float(b[b.index.year == y].mean() / b[b.index.year == y].std() * np.sqrt(252)), 2) for y in range(2020, 2027)}
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); P["CX"] = pd.read_parquet(ROOT / "results/v99/cx_sleeve_prefix.parquet")["CX"].reindex(P.index).fillna(0.0)
b0 = book(P)[0]; out = {"reference (with CX)": per(b0), "ref by year": yr(b0)}


def run(w, var="a"):
    P2 = P.copy(); P2["CXK"] = daily(g["execute"](g["d2h"](w), var)).reindex(P.index).fillna(0.0); return book(P2)[0]


w = k["w"]; b1 = run(w); out["registered"] = per(b1); out["registered by year"] = yr(b1)
V = {"weekend-flat (b)": run(w, "b"), "BTC only": run(w.assign(ETH=0.0)), "ETH only": run(w.assign(BTC=0.0)), "lagged 24 h": run(w.shift(1).fillna(0.0))}
orig = F.cost_frac; F.cost_frac = lambda c, px: 2 * orig(c, px); V["2x costs"] = run(w); F.cost_frac = orig
for n, b in V.items():
    out[n] = per(b)
out["variants passing"] = sum(out[n][2] >= 1.414 + 0.05 for n in V)
out["worst year 2023-26 vs ref"] = round(min(out["registered by year"][y] - out["ref by year"][y] for y in ("2023", "2024", "2025", "2026")), 2)
# diagnostic: the two halves of the composite
for part, keep in (("Coinbase part only", 0), ("Korean part only", 1)):
    ww = pd.DataFrame(0.0, index=w.index, columns=w.columns)
    for c in ("BTC", "ETH"):
        s = (k["ZC"] if keep == 0 else k["ZK"])[c]
        Z = (s - s.rolling(30, min_periods=20).mean()) / s.rolling(30, min_periods=20).std()
        ww[c] = np.where(Z > 1, 0.5, np.where(Z < -1, -0.5, 0.0))
    out[part] = per(run(ww.reindex(w.index).fillna(0.0)))
out["robust"] = bool(out["variants passing"] >= 3 and out["worst year 2023-26 vs ref"] >= -0.3)
print(json.dumps(out, indent=1)); (ROOT / "results/v99/fcx3b.json").write_text(json.dumps(out, indent=1))

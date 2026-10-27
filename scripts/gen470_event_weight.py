"""Gen470 (config/gen470_protocol.json): event-short risk weight x m in the v9.8 book. Writes results/gen470.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
s, _, _ = EL.pnl(idx); V8 = V.drop(columns="cascade limit strict").assign(**{"listing short": s})
orig = CS.v5_weights
def book(m):
    def w(D, sleeves=CS.V5_SLEEVES, weiss_scale=0.5):
        W = orig(D, sleeves, weiss_scale)
        if "listing short" in W:
            W["listing short"] = W["listing short"] * m
        return W
    CS.v5_weights = w
    try:
        return unit(CS.portfolio_v5(V8)[0])
    finally:
        CS.v5_weights = orig
b1 = book(1.0); REF = [shp(b1), per(b1)]
out = {"reference v9.8": REF, "corr event short vs rest (daily, 2022-26)": None, "trials": {}}
rest = unit(CS.portfolio_v5(V8.drop(columns="listing short"))[0])
out["corr event short vs rest (daily, 2022-26)"] = round(float(dd(s.loc["2022":END]).corr(dd(rest.loc["2022":END]))), 3)
for m in (1.5, 2.0):
    b = book(m); out["trials"][str(m)] = {"2022-24": shp(b, "2022", "2024"), "book": [shp(b), per(b)]}
    print(m, out["trials"][str(m)], flush=True)
ch = max(out["trials"], key=lambda k: out["trials"][k]["2022-24"]); r = out["trials"][ch]["book"]
out["chosen"] = ch; out["pass"] = bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))
(ROOT / "results/gen470.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

"""Gen209 (config/gen209_protocol.json): VRP and VIX term structure -> ES/NQ timing. Needs research_data/more2/vix_VIX.parquet and vix_VIX3M.parquet. Writes results/gen209.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
M2 = ROOT / "research_data/more2"
if not (M2 / "vix_VIX.parquet").exists():
    sys.exit("VIX data not downloaded yet (get_vix_data.bat)")
c = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], c)
F, S, TUNE, JUDGE, IX, D, daily_book, monthly = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "IX", "D", "daily_book", "monthly"))
import fbook as B
vix = pd.read_parquet(M2 / "vix_VIX.parquet")["close"].reindex(IX).ffill()
es = D["ES"].r.reindex(IX)
vrp = vix ** 2 / 12 - (es ** 2).rolling(21).sum() * 1e4
ME = IX.to_series().groupby(IX.to_period("M")).max()
vm = vrp.reindex(ME.values); med = vm.rolling(60, min_periods=36).median()
rules = {"VR1": monthly((vm > med).astype(float).reindex(IX).ffill() * 2 - 1, lambda v: 1.0 if v > 0 else 0.0),
         "VR2": monthly(vrp, lambda v: 1.0 if v > 0 else 0.0)}
if (M2 / "vix_VIX3M.parquet").exists():
    v3 = pd.read_parquet(M2 / "vix_VIX3M.parquet")["close"].reindex(IX).ffill(); ts = v3 / vix - 1
    rules.update({"TS1": monthly(ts, lambda v: 1.0 if v < 0 else 0.0), "TS2": monthly(ts, lambda v: 1.0 if v > 0 else 0.0)})
sl = {k: daily_book(pd.DataFrame({r: 0.5 * p for r in ("ES", "NQ")}), ["ES", "NQ"]) for k, p in rules.items()}
fam = {"VRP": ["VR1", "VR2"], "TS": ["TS1", "TS2"]}; rep, enter = {}, {}
for f, ks in fam.items():
    ks = [k for k in ks if k in sl]
    if not ks:
        continue
    t = {k: round(S(sl[k], TUNE), 3) for k in ks}; ch = max(t, key=t.get)
    rep[f] = {"tune": t, "chosen": ch, "2023-26": round(S(sl[ch], JUDGE), 3), "enters": bool(t[ch] > 0.3)}
    if t[ch] > 0.3:
        enter[f] = sl[ch]
out = {"families": rep, "entered": list(enter)}
if enter:
    out.update(B.judge(enter, "gen209"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen209.json", "w"), indent=1)

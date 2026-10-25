"""Gen407 (config/gen407_protocol.json). Writes results/gen407.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\na = ((pnl8")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
dd, shp, per, unit, END, CS, V, B, pnl, days, rel, rel8, pnl8, C6 = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "B", "pnl", "days", "rel", "rel8", "pnl8", "C6"))
cols = ("count_toptrader_long_short_ratio", "count_long_short_ratio")
P = pd.DataFrame({c: B.k5(c).close.resample("1D").last() for c in C6}).reindex(days); r = P.pct_change()
idxr = r.mean(axis=1); beta = r.rolling(60, min_periods=40).cov(idxr).div(idxr.rolling(60, min_periods=40).var(), axis=0).shift(1)
vol = r.rolling(30, min_periods=20).std().shift(1)
def tr(w, mode, freq="D"):
    bt = beta.reindex(w.index, method="ffill") if freq != "D" else beta.reindex(w.index); vv = vol.reindex(w.index, method="ffill") if freq != "D" else vol.reindex(w.index)
    if mode == "A":
        k = (w * bt).sum(axis=1) / (bt * bt).sum(axis=1); out = w - bt.mul(k, axis=0)
    elif mode == "B":
        x = w * vv.median(axis=1).values[:, None] / vv; out = x.sub(x.mean(axis=1), axis=0)
    else:
        out = w
    return out.fillna(0.0)
def sleeve(mode):
    d = sum(pnl(tr(rel(C6, c), mode)) for c in cols) / 2
    s3 = sum(pnl(tr(rel(C6, c).rolling(3, min_periods=1).mean(), mode)) for c in cols) / 2
    h8 = sum(pnl8(tr(rel8(c), mode, "8h")) for c in cols) / 2
    return ((d + s3 + h8) / 3).reindex(V.index).fillna(0.0)
base = sleeve(None); v95 = unit(CS.portfolio_v5(V.assign(**{"relative crowding 6": base}))[0]); REF = (shp(v95), per(v95))
out = {"reference v9.5 (rebuilt)": [REF[0], REF[1]], "trials": {}}
for nm, m in (("A beta-neutral", "A"), ("B inverse-vol", "B")):
    s = sleeve(m); b = unit(CS.portfolio_v5(V.assign(**{"relative crowding 6": s}))[0]); rr = [shp(b), per(b)]
    out["trials"][nm] = {"sleeve": per(s), "book": rr, "pass": bool(rr[0] >= REF[0] + 0.05 and all(rr[1][i] >= REF[1][i] for i in range(3)))}
    print(nm, out["trials"][nm], flush=True)
(ROOT / "results/gen407.json").write_text(json.dumps(out, indent=1)); print(out["reference v9.5 (rebuilt)"])

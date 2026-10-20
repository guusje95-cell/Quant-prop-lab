"""Gen139 (config/gen139_protocol.json): vol-managed long gold in bf (Q1) and as a futures sleeve (Q2). Writes results/gen139.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen127_p6.py")}
src = open(ROOT / "scripts/gen127_p6.py").read(); exec(src.split("vb = CS.portfolio_v5")[0], g)
CS, HB0, per, sh, IDXbf, p6 = (g[k] for k in ("CS", "HB0", "per", "sh", "IDXbf", "p6"))
x = pd.read_parquet(ROOT / "research_data/dukascopy/XAUUSD_1h.parquet")["close"].astype("float64"); x = x[~x.index.duplicated()].sort_index().reindex(IDXbf).ffill(limit=72)
r = x.pct_change().fillna(0.0); dret = r.groupby(r.index.floor("D")).sum(); vol = dret.rolling(20).std() * np.sqrt(252)
w = (0.15 / vol).clip(upper=2.0).shift(1); wh = w.reindex(IDXbf.floor("D")).set_axis(IDXbf).fillna(0.0)
q1 = wh * r - wh.diff().abs().fillna(0.0) * 2e-4
H1 = pd.concat([HB0, p6.rename("vol-managed indices")], axis=1).fillna(0.0)
b1 = CS.portfolio_v5(H1)[0]; b2 = CS.portfolio_v5(pd.concat([H1, q1.rename("vol-managed gold")], axis=1).fillna(0.0))[0]
k1, k2 = per(b1, "2022-01-01"), per(b2, "2022-01-01")
out = {"Q1 sleeve D/T/H": np.round(per(q1, "2020-01-01"), 3).tolist(),
       "bf+P6": [round(sh(b1, "2022-01-01", "2026-09-30"), 3), np.round(k1, 3).tolist()],
       "bf+P6+gold": [round(sh(b2, "2022-01-01", "2026-09-30"), 3), np.round(k2, 3).tolist()]}
out["Q1 pass"] = bool(out["bf+P6+gold"][0] > out["bf+P6"][0] and k2[1] >= k1[1] and k2[2] >= k1[2])
import futures_db as F
f = {"__file__": str(ROOT / "scripts/gen122_futures.py")}
fs = open(ROOT / "scripts/gen122_futures.py").read(); exec(fs[:fs.index("# F1 / F2")] + fs[fs.index("# daily helpers"):fs.index("# F3")], f)
RG = f["D"]["GC"].r; rv = RG.rolling(20).std() * np.sqrt(252); WG = pd.DataFrame({"GC": (0.15 / rv).clip(upper=2.0).shift(1).fillna(0.0)})
q2 = f["daily_book"](WG, ["GC"]); kq = [round(F.sharpe(q2, a, b), 3) for a, b in F.SPLITS]
out["Q2 GC sleeve D/T/H"] = kq; out["Q2 pass"] = bool(kq[0] > 0 and kq[1] >= 0.5 and kq[2] >= 0.3)
q2.to_frame("Q2 vol-managed gold GC").to_parquet(ROOT / "results/gen139_q2_daily.parquet")
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen139.json", "w"), indent=1)

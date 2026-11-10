"""EX-1d (protocol research/v99/ex1d_protocol.json): fill delay of bf2.8's index CFD sleeve. Writes results/v99/ex1d_index_delay.json."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
g0 = {"__file__": str(ROOT / "scripts/v99/ex1_delay.py"), "__name__": "ex1"}
exec((ROOT / "scripts/v99/ex1_delay.py").read_text().split("\nout = {}\n")[0], g0)
g2 = g0["run"]("cn2_cfd_netting.py", "sv = C.dd(sep - netc)"); delay_pnl = g0["delay_pnl"]
C, IX = g2["C"], g2["IX"]
sys.path.insert(0, str(ROOT / "scripts")); import index_sleeve as IS
pos, pnl = IS.sleeve(IX)
n = "vol-managed indices"; scale = (g2["Wh"][n] * g2["mh"]).values[:, None]
P = {}
for s in ("US100", "US500", "US30"):
    x = pd.read_parquet(ROOT / f"research_data/dukascopy/{s}_5m.parquet")["close"]; x.index = x.index + pd.Timedelta(minutes=5)   # bar END
    P[s] = x[~x.index.duplicated()]
P = pd.DataFrame(P)
D = lambda s: C.dd(s).reindex(pd.date_range("2021-06-01", "2026-09-30")).fillna(0.0)
chk = pd.concat([D(pnl), D(g2["H"][n].reindex(IX).fillna(0.0))], axis=1).loc["2022":"2026-09-30"].corr().iloc[0, 1]
base = D(g2["book"] + (g2["sep"] - g2["netc"]))
out = {"check: index sleeve P&L vs bf2.8 sleeve (daily corr)": round(float(chk), 3), "base (CN-2 net)": C.full(base)}
sp = pos * scale
for d in (5, 15, 30):
    x = D(delay_pnl(sp, P, d)); out[f"delay {d} min"] = C.full(base + x)
    out[f"delay {d} min: cost, % of book a year"] = round(float(-x.loc["2022":"2026-09-30"].mean() * 365 * 100), 3)
print(json.dumps(out, indent=1)); (ROOT / "results/v99/ex1d_index_delay.json").write_text(json.dumps(out, indent=1))

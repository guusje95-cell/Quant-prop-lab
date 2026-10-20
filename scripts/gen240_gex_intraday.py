"""Gen240 (config/gen240_protocol.json): GEX-regime intraday momentum / reversal on ES/NQ 1-minute. Needs research_data/more2/squeeze_dix.csv.
Writes results/gen240.json (+ gen240_daily.parquet)."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
f = ROOT / "research_data/more2/squeeze_dix.csv"
if not f.exists():
    sys.exit("squeeze_dix.csv not downloaded yet (get_squeeze_dix.bat)")
import futures_db as F
w = {"__file__": str(ROOT / "scripts/gen148_r1_windows.py")}; exec(open(ROOT / "scripts/gen148_r1_windows.py").read().split("\ndef snaps(")[0], w)
load, I = w["load"], w["I"]
g = pd.read_csv(f); g.columns = [c.strip().lower() for c in g.columns]; g["date"] = pd.to_datetime(g["date"]); g = g.set_index("date").sort_index()
gex = g["gex"].astype(float)
lo_q, hi_q = gex.rolling(252, min_periods=200).quantile(0.3), gex.rolling(252, min_periods=200).quantile(0.7)
REG = pd.Series(np.where(gex < lo_q, -1, np.where(gex > hi_q, 1, 0)), index=gex.index).shift(1)   # value of t-1 used on day t


def daily(root, B):
    B = B[B.index.weekday < 5]; t = B.index.strftime("%H:%M"); day = B.index.normalize()
    o = B[t == "09:30"].groupby(day[t == "09:30"]).agg(o=("open", "first"), oi=("instrument_id", "first"))
    p10 = B[t < "10:00"].groupby(day[t < "10:00"]).agg(p10=("close", "last"), i10=("instrument_id", "last"))
    p55 = B[t < "15:55"].groupby(day[t < "15:55"]).agg(p55=("close", "last"), i55=("instrument_id", "last"))
    x = o.join(p10, how="inner").join(p55, how="inner"); x = x[(x.oi == x.i10) & (x.i10 == x.i55)]
    x["first"] = x.p10 / x.o - 1; x["rest"] = x.p55 / x.p10 - 1; x["cost"] = 2 * F.cost_frac(root, x.p10)
    x["reg"] = REG.reindex(x.index); return x


def sleeve(x, both):
    s = np.where(x.reg == -1, np.sign(x["first"]), np.where((x.reg == 1) & both, -np.sign(x["first"]), 0.0))
    s = pd.Series(s, index=x.index); return (0.5 * (s * x.rest - s.abs() * x.cost)).fillna(0.0)


DX = {r: daily(r, load(r)) for r in ("ES", "NQ")}; NQo = daily("NQ", load("NQ", old=True))
SPL, sh = I["SPL"], I["sharpe"]; res = {}
for name, both in (("LGM", False), ("BOTH", True)):
    p = pd.concat([sleeve(DX[r], both) for r in DX], axis=1).fillna(0.0).sum(axis=1)
    res[name] = {"ES+NQ 2018-20 / 21-23 / 24-26": [round(sh(p, a, b), 3) for a, b in SPL], "NQ 2011-17": round(sh(sleeve(NQo, both), "2011-01-01", "2017-12-31"), 3),
                 "sel": round(sh(p, "2018-01-01", "2023-12-31"), 3), "days traded / yr": round(float((p != 0).mean() * 252), 1)}
    print(name, res[name], flush=True)
ch = max(res, key=lambda k: res[k]["sel"]); v = res[ch]
out = {"variants": res, "chosen": ch, "pass": bool(v["ES+NQ 2018-20 / 21-23 / 24-26"][0] > 0 and v["ES+NQ 2018-20 / 21-23 / 24-26"][1] >= 0.3
                                                   and v["ES+NQ 2018-20 / 21-23 / 24-26"][2] >= 0.3 and v["NQ 2011-17"] > 0)}
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen240.json", "w"), indent=1)

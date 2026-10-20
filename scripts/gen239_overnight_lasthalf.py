"""Gen239 (config/gen239_protocol.json): overnight return -> last half hour, ES/NQ 1-minute. Writes results/gen239.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
w = {"__file__": str(ROOT / "scripts/gen148_r1_windows.py")}; exec(open(ROOT / "scripts/gen148_r1_windows.py").read().split("\ndef snaps(")[0], w)
load, I = w["load"], w["I"]


def daily(root, B):
    B = B[B.index.weekday < 5]; t = B.index.strftime("%H:%M"); day = B.index.normalize()
    o = B[t == "09:30"].groupby(day[t == "09:30"]).agg(o=("open", "first"), oi=("instrument_id", "first"))
    a = B[t == "15:30"].groupby(day[t == "15:30"]).agg(a=("open", "first"), ai=("instrument_id", "first"))
    m = t < "16:00"; c = B[m].groupby(day[m]).agg(c=("close", "last"), ci=("instrument_id", "last"))
    x = o.join(a, how="inner").join(c, how="inner"); x["pc"] = x.c.shift(1); x["pci"] = x.ci.shift(1)
    x["on"] = (x.o / x.pc - 1).where(x.oi == x.pci); x["sd"] = x.on.rolling(20, min_periods=15).std().shift(1)
    x["last"] = (x.c / x.a - 1).where(x.ai == x.ci); x["cost"] = 2 * F.cost_frac(root, x.a)
    return x


def sleeve(x, k):
    s = np.sign(x.on).where(x.on.abs() > k * x.sd, 0.0)
    return (0.5 * (s * x.last - s.abs() * x.cost)).fillna(0.0)


DX = {r: daily(r, load(r)) for r in ("ES", "NQ")}; NQo = daily("NQ", load("NQ", old=True))
SPL = I["SPL"]; sh = I["sharpe"]; res = {}
for k in (0, 0.5):
    p = pd.concat([sleeve(DX[r], k) for r in DX], axis=1).fillna(0.0).sum(axis=1)
    res[k] = {"pooled": [round(sh(p, a, b), 3) for a, b in SPL], "NQ 2010-17": round(sh(sleeve(NQo, k), "2010-06-01", "2017-12-31"), 3),
              "sel": round(sh(p, "2018-01-01", "2023-12-31"), 3)}
    print(k, res[k], flush=True)
ch = max(res, key=lambda k: res[k]["sel"]); v = res[ch]
out = {"grid": {str(k): v_ for k, v_ in res.items()}, "chosen k": ch,
       "pass": bool(v["pooled"][0] > 0 and v["pooled"][1] >= 0.3 and v["pooled"][2] >= 0.3 and v["NQ 2010-17"] > 0)}
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen239.json", "w"), indent=1)

"""Gen244 (config/gen244_protocol.json): QQQ closing imbalance -> NQ overnight reversal. Writes results/gen244.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen242_close_imbalance.py").read().split("\nB = load(\"NQ\")")[0]
g = {"__file__": str(ROOT / "scripts/gen242_close_imbalance.py")}; exec(src, g)
F, load, I, side, dollar = g["F"], g["load"], g["I"], g["side"], g["dollar"]
B = load("NQ"); B = B[B.index.weekday < 5]; t = B.index.strftime("%H:%M"); day = B.index.normalize()
def at(mask, col, how):
    x = B[mask]; return x.groupby(day[mask]).agg(p=(col, how), i=("instrument_id", how))
c16 = at(t < "16:00", "close", "last"); o18 = at(t == "18:00", "open", "first"); o930 = at(t == "09:30", "open", "first")
x = c16.rename(columns={"p": "c16", "i": "i16"}).join(o18.rename(columns={"p": "o18", "i": "i18"}), how="left")
nx = o930.rename(columns={"p": "o930", "i": "i930"}).shift(-1).reindex(x.index)            # next session's 09:30 (index = signal day)
nx.index = x.index; x = x.join(nx)
x["side"] = side.reindex(x.index).fillna(0.0); x["dollar"] = dollar.reindex(x.index); x["med"] = x.dollar.rolling(20, min_periods=10).median().shift(1)
s = -x.side.where(x.dollar > x.med, 0.0)
cost = 2 * F.cost_frac("NQ", x.c16)
r18 = (x.o930 / x.o18 - 1).where(x.i18 == x.i930); r16 = (x.o930 / x.c16 - 1).where(x.i16 == x.i930)
SPL, sh = I["SPL"], I["sharpe"]; res = {}
for name, r in (("ON18", r18), ("ON16", r16)):
    p = (0.5 * (s * r - s.abs() * cost)).fillna(0.0).loc["2018-06-01":]
    res[name] = {"2018-20 / 21-23 / 24-26": [round(sh(p, a, b), 3) for a, b in SPL], "sel": round(sh(p, "2018-06-01", "2023-12-31"), 3)}
    print(name, res[name], flush=True)
ch = max(res, key=lambda k: res[k]["sel"]); v = res[ch]["2018-20 / 21-23 / 24-26"]
out = {"variants": res, "chosen": ch, "pass": bool(v[0] > 0 and v[1] >= 0.3 and v[2] >= 0.3)}
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen244.json", "w"), indent=1)

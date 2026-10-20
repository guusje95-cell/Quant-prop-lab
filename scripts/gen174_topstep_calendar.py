"""Gen174 (config/gen174_protocol.json): session-only equity calendar book (Topstep-compatible). Writes results/gen174.json + gen174_daily.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen161_vm_calendar.py")}; exec(open(ROOT / "scripts/gen161_vm_calendar.py").read().split("res = {}")[0], c)
F, EQ, M = c["F"], c["EQ"], c["M"]
I = {"__file__": str(ROOT / "scripts/gen124_intraday.py")}; exec(open(ROOT / "scripts/gen124_intraday.py").read().split("def news(")[0], I)
cal = pd.concat(M.values(), axis=1).max(axis=1); act = set(cal[cal > 0].index)


def minute(root):
    B = I["bars_futures"](root); B = B[B.index.weekday < 5]; t = B.index.strftime("%H:%M"); day = B.index.normalize()
    o = B[t == "09:30"].groupby(day[t == "09:30"]).agg(o=("open", "first"), oi=("instrument_id", "first"))
    m = t < "16:00"; cl = B[m].groupby(day[m]).agg(c=("close", "last"), ci=("instrument_id", "last"))
    x = o.join(cl, how="inner"); x = x[x.oi == x.ci]
    on = pd.Series(x.index.isin(list(act)).astype(float), index=x.index)
    return 0.5 * on * (x.c / x.o - 1 - 2 * F.cost_frac(root, x.o))


def hourly(root):
    f = F.front(root); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod(); wk = (t.wd < 5).to_numpy()
    pick = lambda hh: pz[wk & (t.h == hh).to_numpy()].groupby(t.date[wk & (t.h == hh).to_numpy()]).last()
    c09, c16 = pick(8), pick(15); r = (c16 / c09.reindex(c16.index) - 1)
    on = pd.Series(r.index.isin(list(act)).astype(float), index=r.index)
    return 0.25 * on * (r.fillna(0.0) - 2 * F.daily(root).cost.reindex(r.index).ffill())


pm = pd.concat([minute(r) for r in ("ES", "NQ")], axis=1).fillna(0.0).sum(axis=1)
ph = pd.concat([hourly(r) for r in EQ], axis=1).fillna(0.0).sum(axis=1)
out = {"1-minute ES+NQ 2018-20 / 21-23 / 24-26": [round(I["sharpe"](pm, a, b), 3) for a, b in I["SPL"]],
       "hourly 4-index 2010-17 / 2018-22 / 2023-26": [round(F.sharpe(ph, *s), 3) for s in F.SPLITS]}
v = out["1-minute ES+NQ 2018-20 / 21-23 / 24-26"]
out["pass"] = bool(v[0] > 0 and v[1] >= 0.3 and v[2] >= 0.3 and out["hourly 4-index 2010-17 / 2018-22 / 2023-26"][0] > 0)
yrs = pm.loc["2018":]; out["1-minute by year"] = {str(y): round(I["sharpe"](pm, f"{y}-01-01", f"{y}-12-31"), 2) for y in range(2018, 2027)}
out["active days per year (approx)"] = int(len(act) / 16.3)
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen174.json", "w"), indent=1)
pd.DataFrame({"minute_esnq": pm, "hourly_4idx": ph}).to_parquet(ROOT / "results/gen174_daily.parquet")

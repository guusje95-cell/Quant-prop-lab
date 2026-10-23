"""Gen328 part 2 (config/gen328_protocol.json): per-coin position caps on the v8.6 net positions (Gen323 model, 5 bp, $1,000 band,
risk 2.0). Appends to results/gen328.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
_p = Path(__file__).resolve().parent / "gen323_execution.py"; _s = _p.read_text()
exec(compile(_s[:_s.index("base, pnl0, E0 = run(net)")], str(_p), "exec"))


def stats(pnl, E):
    d = pnl.groupby(pnl.index.floor("D")).sum() * RISK; eq = (1 + d).cumprod()
    cp = (E * r.reindex(E.index)) * RISK; cd = cp.groupby(cp.index.floor("D")).sum()
    return {"worst day %": round(float(d.min()) * 100, 2), "max drawdown %": round(float((eq / eq.cummax() - 1).min()) * 100, 1),
            "worst single-coin day %": round(float(cd.min().min()) * 100, 2), "coin-days losing > 3% of the account": int((cd < -0.03).sum().sum())}


expo = (net.abs() * RISK); mx = expo.max(axis=1)
out = {"largest single-coin position (share of equity, risk 2.0): median / p90 / p99 / max":
       [round(float(mx.median()), 3), round(float(mx.quantile(0.9)), 3), round(float(mx.quantile(0.99)), 3), round(float(mx.max()), 3)],
       "coin most often largest": expo.idxmax(axis=1).value_counts().head(3).to_dict()}
o, p0, E0 = run(net, band_usd=1000); base = {**o, **stats(p0, E0)}; out["no cap"] = base; print("no cap", base, flush=True)
for c in (0.40, 0.30, 0.25, 0.20):
    T = net.clip(lower=-c / RISK, upper=c / RISK)
    o, p, E = run(T, band_usd=1000); st = {**o, **stats(p, E)}
    st["adopt (Sharpe >= base - 0.05, worst day and max DD better)"] = bool(st["sharpe D/T/H"][0] >= base["sharpe D/T/H"][0] - 0.05
                                                                           and st["worst day %"] > base["worst day %"] and st["max drawdown %"] > base["max drawdown %"])
    out[f"cap {int(c * 100)}% of equity per coin"] = st; print(c, st, flush=True)
f = ROOT / "results/gen328.json"; R = json.load(open(f)); R["2 per-coin caps v8.6"] = out; json.dump(R, open(f, "w"), indent=1, default=str)

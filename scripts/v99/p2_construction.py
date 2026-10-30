"""v9.9 P2 (research/v99/p2_protocol.json): portfolio_v5 construction knobs, selected on 2022-24, judged once on 2025-26.
Writes results/v99/p2_construction.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL


def weights(D, sleeves, win, weiss_scale=0.5):
    W = pd.DataFrame(np.nan, index=D.index, columns=list(sleeves))
    for m in D.index[~D.index.to_period("M").duplicated()]:
        hist = D.loc[m - pd.Timedelta(days=win):m - pd.Timedelta(days=1)]
        live = [c for c in sleeves if (hist[c] != 0).sum() >= (6 if c == "Weiss expiry" else 30) and hist[c].std() > 0]
        if len(live) < 2:
            continue
        w = pd.Series(0.10 / (hist[live].std().to_numpy()), index=live) / len(live)
        if "Weiss expiry" in w:
            w["Weiss expiry"] *= weiss_scale
        W.loc[m, :] = 0.0; W.loc[m, w.index] = w.to_numpy()
    return W.ffill().fillna(0.0)


def portfolio(H, win=365, vwin=30, cap=1.5, vol=0.15, start="2022-01-01"):
    D = H.groupby(H.index.floor("D")).sum(); W = weights(D, list(H.columns), win)
    Wh = W.reindex(H.index.floor("D")).set_axis(H.index)
    raw = (H * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (vol / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1); x1 = rawd * lvl
    tgt = (vol / (x1.rolling(vwin).std() * np.sqrt(365))).clip(upper=cap).shift(1)
    mult = (lvl * tgt).loc[start:]
    return (raw * mult.reindex(raw.index.floor("D")).set_axis(raw.index)).loc[start:].dropna()


V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a, z):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
def book(**kw):
    b = unit(portfolio(V8, **kw)); return {"dev 2022-24": shp(b, "2022", "2024"), "holdout 2025-26": shp(b, "2025", "2026-09-30"), "full": shp(b, "2022", "2026-09-30")}
assert abs(float((portfolio(V8) - CS.portfolio_v5(V8)[0]).abs().max())) < 1e-12        # the copy equals the frozen function
VAR = {"current": {}, "budget 180": {"win": 180}, "budget 730": {"win": 730}, "vol window 14": {"vwin": 14}, "vol window 60": {"vwin": 60},
       "cap 1.25": {"cap": 1.25}, "cap 2.0": {"cap": 2.0}}
out = {"variants": {}}
for k, kw in VAR.items():
    out["variants"][k] = book(**kw); print(k, out["variants"][k], flush=True)
best = max(VAR, key=lambda k: (out["variants"][k]["dev 2022-24"], k == "current")); out["chosen"] = best
c, r = out["variants"][best], out["variants"]["current"]
out["adopt"] = bool(best != "current" and c["holdout 2025-26"] >= r["holdout 2025-26"] + 0.05 and c["full"] >= r["full"])
(ROOT / "results/v99/p2_construction.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in ("chosen", "adopt")}))

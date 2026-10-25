"""Gen388 (config/gen388_protocol.json). Writes results/gen388.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen384_positioning.py").read().split("b380 = pd.read_parquet")[0]
g = {"__file__": str(ROOT / "scripts/gen384_positioning.py")}; exec(compile(src, "g384", "exec"), g)
POOL, dd, shp, per, unit, END, CS, base = (g[k] for k in ("POOL", "dd", "shp", "per", "unit", "END", "CS", "base"))
kept = json.loads((ROOT / "results/gen384.json").read_text())["kept"]
s3 = open(ROOT / "scripts/gen383_ensembles.py").read().split("T = {")[0]; g3 = {"__file__": str(ROOT / "scripts/gen383_ensembles.py")}; exec(compile(s3, "g383", "exec"), g3)
te, ke = g3["te"], g3["ke"]
b384 = pd.read_parquet(ROOT / "results/gen384_basket_hourly.parquet")["basket"].reindex(base.index).fillna(0.0)
H92 = base.assign(**{"trend 4h": te, "alt kimchi": ke, "diversifier basket": b384})
v92 = unit(CS.portfolio_v5(H92)[0]); REF = (shp(v92), per(v92))
# --- part A: walk-forward Sharpe-weighted basket
M = pd.DataFrame({k: POOL[k] for k in kept}).reindex(base.index).fillna(0.0); Md = dd(M)
def sharpe_basket(win):
    months = Md.index[~Md.index.to_period("M").duplicated()]; Wm = pd.DataFrame(np.nan, index=Md.index, columns=kept)
    for m in months:
        h = Md.loc[m - pd.Timedelta(days=win):m - pd.Timedelta(days=1)]
        sd = h.std(); sr = h.mean() / sd * np.sqrt(365); n = (h != 0).sum()
        w = pd.Series(np.where(n >= 180, sr.clip(lower=0), 1.0), index=kept) / sd.replace(0, np.nan)
        Wm.loc[m] = (w / w.abs().sum()).fillna(0.0).to_numpy() if w.abs().sum() > 0 else 0.0
    Wh = Wm.ffill().fillna(0.0).reindex(M.index.floor("D")).set_axis(M.index)
    bh = (M * Wh).sum(axis=1); return bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
A = {f"A{i} {w}d": sharpe_basket(w) for i, w in ((1, 365), (2, 730))}
resA = {}
for k, bh in A.items():
    b = unit(CS.portfolio_v5(H92.assign(**{"diversifier basket": bh}))[0]); resA[k] = {"basket": per(bh), "2022-24": shp(b, "2022", "2024"), "book": [shp(b), per(b)]}
chA = max(resA, key=lambda k: resA[k]["2022-24"]); rA = resA[chA]["book"]; passA = bool(rA[0] >= REF[0] + 0.05 and all(rA[1][i] >= REF[1][i] for i in range(3)))
# --- part B: sleeve weight window
def v5w(D, sleeves, win, weiss_scale=0.5):
    W = pd.DataFrame(np.nan, index=D.index, columns=list(sleeves))
    for m in D.index[~D.index.to_period("M").duplicated()]:
        hist = D.loc[m - pd.Timedelta(days=win):m - pd.Timedelta(days=1)]
        live = [c for c in sleeves if (hist[c] != 0).sum() >= (6 if c == "Weiss expiry" else min(30, win // 6)) and hist[c].std() > 0]
        if len(live) < 2:
            continue
        w = pd.Series(0.10 / hist[live].std().to_numpy(), index=live) / len(live)
        if "Weiss expiry" in w:
            w["Weiss expiry"] *= weiss_scale
        W.loc[m, :] = 0.0; W.loc[m, w.index] = w.to_numpy()
    return W.ffill().fillna(0.0)
def p5(H, win, vol=0.15, start="2022-01-01"):
    D = H.groupby(H.index.floor("D")).sum(); W = v5w(D, list(H.columns), win)
    raw = (H * W.reindex(H.index.floor("D")).set_axis(H.index)).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (vol / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1); tgt = (vol / ((rawd * lvl).rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1)
    mu = (lvl * tgt).loc[start:]; return (raw * mu.reindex(raw.index.floor("D")).set_axis(raw.index)).loc[start:].dropna()
chk = shp(unit(p5(H92, 365)))
resB = {}
for k, w in (("B1 180d", 180), ("B2 90d", 90)):
    b = unit(p5(H92, w)); resB[k] = {"2022-24": shp(b, "2022", "2024"), "book": [shp(b), per(b)]}
chB = max(resB, key=lambda k: resB[k]["2022-24"]); rB = resB[chB]["book"]; passB = bool(rB[0] >= REF[0] + 0.05 and all(rB[1][i] >= REF[1][i] for i in range(3)))
out = {"reference v9.2": [REF[0], REF[1]], "check 365-day window reproduces v9.2": chk, "A": resA, "A chosen": chA, "A pass": passA, "B": resB, "B chosen": chB, "B pass": passB}
if passA and passB:
    b = unit(p5(H92.assign(**{"diversifier basket": A[chA]}), int(chB.split()[1][:-1]))); out["A + B"] = [shp(b), per(b)]
(ROOT / "results/gen388.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

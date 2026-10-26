"""Gen438 (config/gen438_protocol.json): shrunk-Sharpe sleeve weights for the v9.6 book. Writes results/gen438.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, _ = LL.pnl(idx); H = V.assign(**{"listing short": ls}); D = dd(H)
def weights(window):
    W = pd.DataFrame(np.nan, index=D.index, columns=H.columns)
    for m in D.index[~D.index.to_period("M").duplicated()]:
        h365 = D.loc[m - pd.Timedelta(days=365):m - pd.Timedelta(days=1)]
        live = [c for c in H.columns if (h365[c] != 0).sum() >= (6 if c == "Weiss expiry" else 30) and h365[c].std() > 0]
        if len(live) < 2:
            continue
        hs = D.loc[(m - pd.Timedelta(days=window)) if window else D.index[0]:m - pd.Timedelta(days=1), live]
        n_obs = (hs != 0).sum()
        sr = (hs.mean() / hs.std() * np.sqrt(365)).where(hs.notna().sum() >= 365)
        sr = sr.fillna(sr.mean() if sr.notna().any() else 1.0)
        s = (0.5 * sr + 0.5 * sr.mean()).clip(lower=0.0)
        s = s / s.mean() if s.mean() > 0 else pd.Series(1.0, index=live)
        w = 0.10 * s / h365[live].std() / len(live)
        if "Weiss expiry" in w:
            w["Weiss expiry"] *= 0.5
        W.loc[m, :] = 0.0; W.loc[m, w.index] = w.to_numpy()
    return W.ffill().fillna(0.0)
def book(W):
    Wh = W.reindex(H.index.floor("D")).set_axis(H.index); raw = (H * Wh).sum(axis=1); rawd = dd(raw)
    lvl = (0.15 / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1)
    tgt = (0.15 / ((rawd * lvl).rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1); mu = (lvl * tgt).loc["2022-01-01":]
    return unit((raw * mu.reindex(raw.index.floor("D")).set_axis(raw.index)).loc["2022-01-01":].dropna())
ref = unit(CS.portfolio_v5(H)[0]); REF = (shp(ref), per(ref)); REF_R = (3.161, [2.775, 3.919, 2.576])
chk = book(CS.v5_weights(D, list(H.columns)))
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
out = {"reference v9.6 (live timing)": [REF[0], REF[1]], "reference v9.6 (research)": REF_R, "check equal-risk replica": [shp(chk), per(chk)], "trials": {}}
for k, win in (("A shrunk Sharpe, 730 days", 730), ("B shrunk Sharpe, expanding", None)):
    W = weights(win); b = book(W); r = [shp(b), per(b)]
    last = W.iloc[-1]; share = (last * D.loc["2025":].std()).pipe(lambda x: x / x.sum())
    out["trials"][k] = {"book": r, "pass": bool(ok(r, REF) and ok(r, REF_R)), "risk share at the end": {c: round(float(v), 3) for c, v in share.items()}}
(ROOT / "results/gen438.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

"""v9.9 R3 (research/v99/r3_protocol.json): walk-forward, heavily shrunk mean-variance risk tilt on the v9.8 sleeves. Writes results/v99/r3_allocation.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
END = "2026-09-30"
H = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet").drop(columns="port").loc[:END + " 23:00"]
D = H.groupby(H.index.floor("D")).sum(); cols = list(H.columns)
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
qs = pd.date_range("2021-01-01", END, freq="QS")
def multipliers(lam):
    M = pd.DataFrame(1.0, index=qs, columns=cols); prev = pd.Series(1.0, index=cols); hist_log = {}
    for q in qs:
        past = D.loc[:q - pd.Timedelta(days=1)]
        el = [c for c in cols if (past[c] != 0).sum() >= (12 if c == "Weiss expiry" else 365) and len(past[c].loc[past[c].ne(0).idxmax():]) >= 365]
        m = pd.Series(1.0, index=cols)
        if len(el) >= 3:
            X = pd.concat([past[c].loc[past[c].ne(0).idxmax():] for c in el], axis=1).fillna(0.0)
            mu = X.mean() / X.std(); mu = 0.5 * mu + 0.5 * mu.mean()
            C = 0.5 * X.corr().to_numpy() + 0.5 * np.eye(len(el))
            b = pd.Series(np.maximum(0, np.linalg.solve(C, mu.to_numpy())), index=el)
            if b.sum() > 0:
                b = b / b.mean(); m[el] = (1 + lam * (b - 1)).clip(0.5, 2.0)
        m = prev + (m - prev).clip(-0.5, 0.5); M.loc[q] = m; prev = m
    return M
orig = CS.v5_weights
def book(M):
    def w(Dd, sleeves=CS.V5_SLEEVES, weiss_scale=0.5):
        W = orig(Dd, sleeves, weiss_scale); mm = M.reindex(W.index, method="ffill").fillna(1.0)
        return W * mm[W.columns]
    CS.v5_weights = w
    try:
        return unit(CS.portfolio_v5(H)[0])
    finally:
        CS.v5_weights = orig
b0 = unit(CS.portfolio_v5(H)[0]); out = {"v9.8 (equal risk)": [shp(b0), per(b0)], "trials": {}}
for lam in (0.25, 0.5, 1.0):
    M = multipliers(lam); b = book(M)
    out["trials"][str(lam)] = {"2022-24": shp(b, "2022", "2024"), "book": [shp(b), per(b)], "by year": [shp(b, y, y) for y in ("2022", "2023", "2024", "2025", "2026")],
                               "mean multiplier 2022-26": M.loc["2022":].mean().round(2).to_dict(), "multiplier last quarter": M.iloc[-1].round(2).to_dict()}
    print(lam, out["trials"][str(lam)]["book"], flush=True)
ch = max(out["trials"], key=lambda k: out["trials"][k]["2022-24"]); r = out["trials"][ch]["book"]
out["chosen lambda"] = ch; out["promote"] = bool(r[0] >= out["v9.8 (equal risk)"][0] + 0.05 and all(r[1][i] >= out["v9.8 (equal risk)"][1][i] for i in range(3)))
(ROOT / "results/v99/r3_allocation.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

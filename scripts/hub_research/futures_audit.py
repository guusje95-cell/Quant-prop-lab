"""F1 (descriptive): honest audit of the 15-sleeve futures book. Writes results/hub_research/futures_audit.json.
  1. book Sharpe by split / year, and with point-in-time EQR weights
  2. planning Sharpe = SR - E[max SR of N zero-edge trials] (project method, null variance 1/T) for N around the futures trial count
  3. ES/NQ beta: correlation, beta-adjusted Sharpe by split, and its planning value
  4. sleeves: stand-alone splits, ES/NQ appraisal 2010-22, leave-one-out marginal on the book, risk share by asset class"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import fbook
import futures_db as F
G = 0.5772156649
emax = lambda N: (1 - G) * norm.ppf(1 - 1 / N) + G * norm.ppf(1 - 1 / (N * np.e))
CLASS = {"F5": "equity", "P1": "equity", "K3": "equity", "R1": "equity", "T1": "equity", "T2": "equity", "FC": "equity", "MM": "equity",
         "OIL": "equity", "F3": "rates", "BC": "rates", "A3": "rates", "G1": "multi-asset", "U5": "multi-asset", "SH": "energy"}
S = fbook.sleeves(); book = fbook.build(S); spl = lambda x: [round(F.sharpe(x, a, z), 3) for a, z in F.SPLITS]
out = {"book splits 2010-17 / 2018-22 / 2023-26": spl(book), "book full 2010-06..2026-09": round(F.sharpe(book, "2010-06-01", "2026-09-30"), 3),
       "by year": {str(y): round(F.sharpe(book, str(y), str(y)), 2) for y in range(2011, 2027)}}
# trial count: protocols whose config mentions futures data (hub experiments table), keyword heuristic
try:
    import sqlite3
    c = sqlite3.connect(ROOT / "hub_data/hub.sqlite")
    n = 0
    for k, t, cfg in c.execute("SELECT key, trials_added, config FROM experiments WHERE kind='protocol'"):
        s = (cfg or "").lower()
        if any(w in s for w in ("futures", "databento", "es+nq", "cme")) and "crypto" not in s[:400]:
            n += t or 0
    out["futures trials (heuristic count of registered protocols)"] = n
except Exception as e:                                                       # noqa: BLE001 - descriptive only
    out["futures trials (heuristic count of registered protocols)"] = f"unavailable: {e}"
NS = [100, 300, 460, 1000]
def plan(x, a, z):
    x = x.loc[a:z]; x = x[x.index.weekday < 5]; T = len(x); sr = x.mean() / x.std() * np.sqrt(252)
    return {"observed": round(float(sr), 3), "days": T, **{f"N={N}": round(float(sr - emax(N) / np.sqrt(T) * np.sqrt(252)), 3) for N in NS}}
out["planning Sharpe, full 2010-26"] = plan(book, "2010-06-01", "2026-09-30")
out["planning Sharpe, 2023-26 only"] = plan(book, "2023-01-01", "2026-09-30")
bh = pd.concat([F.daily(r).r for r in ("ES", "NQ")], axis=1).mean(axis=1)
beta = {}; resid = []
for a, z in F.SPLITS:
    x = pd.concat([book, bh], axis=1).dropna().loc[a:z]; x = x[x.index.weekday < 5]
    b = np.cov(x.iloc[:, 0], x.iloc[:, 1])[0, 1] / x.iloc[:, 1].var(); r = x.iloc[:, 0] - b * x.iloc[:, 1]; resid.append(r)
    beta[f"{a[:4]}-{z[:4]}"] = {"corr": round(float(x.corr().iloc[0, 1]), 2), "beta": round(float(b), 3),
                                "beta-adjusted Sharpe": round(float(r.mean() / r.std() * np.sqrt(252)), 3),
                                "ES/NQ buy-and-hold Sharpe": round(float(x.iloc[:, 1].mean() / x.iloc[:, 1].std() * np.sqrt(252)), 3)}
out["ES/NQ beta by split"] = beta
out["planning Sharpe of the beta-adjusted book, full 2010-26"] = plan(pd.concat(resid), "2010-06-01", "2026-09-30")
Sw = S[S.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0); T = Sw.loc[:"2022-12-31"]
w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
cov = (Sw.loc["2023":] * w).cov(); rc = (cov.sum(axis=1) / cov.values.sum())
sl = {}
for k in S.columns:
    loo = fbook.build(S.drop(columns=k))
    sl[k] = {"class": CLASS.get(k, "?"), "alone": list(F.splits(S[k])), "appraisal 2010-22": round(fbook.appraisal(S[k]), 2),
             "EQR weight": round(float(w[k]), 3), "risk share 2023-26": round(float(rc[k]), 3),
             "book 2023-26 without it": round(F.sharpe(loo, *F.SPLITS[2]), 3)}
out["sleeves"] = sl
out["risk share 2023-26 by class"] = {c: round(float(sum(v["risk share 2023-26"] for v in sl.values() if v["class"] == c)), 3) for c in set(CLASS.values())}
eq = [k for k in S if CLASS.get(k) == "equity"]; ne = [k for k in S if CLASS.get(k) != "equity"]
out["sub-books (EQR, same construction)"] = {"equity-timing sleeves only": spl(fbook.build(S[eq])), "non-equity sleeves only": spl(fbook.build(S[ne]))}
p = ROOT / "results/hub_research/futures_audit.json"; p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

"""Gen476 (config/gen476_protocol.json): EIA inventory / storage sleeves for the futures book. Writes results/gen476.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import fbook
import futures_db as F
E = ROOT / "research_data/eia"


def petroleum(code):
    d = pd.read_excel(E / f"{code}.xls", sheet_name="Data 1", header=None, skiprows=3)
    s = pd.Series(pd.to_numeric(d[1], errors="coerce").to_numpy(), index=pd.to_datetime(d[0], errors="coerce"))
    return s[s.index.notna()].dropna().sort_index()


def gas():
    d = pd.read_excel(E / "ngshistory.xls", sheet_name="html_report_history", header=None)
    d = d[pd.to_datetime(d[0], errors="coerce").notna()]
    s = pd.Series(pd.to_numeric(d[9], errors="coerce").to_numpy(), index=pd.to_datetime(d[0]))
    return s.dropna().sort_index()


def norm(s):
    """mean of the same ISO week in the previous 5 years (only past data)"""
    wk = s.index.isocalendar().week.to_numpy(); yr = s.index.year.to_numpy(); out = np.full(len(s), np.nan)
    for i in range(len(s)):
        m = (wk == wk[i]) & (yr < yr[i]) & (yr >= yr[i] - 5)
        if m.sum() >= 5:
            out[i] = s.to_numpy()[m].mean()
    return pd.Series(out, index=s.index)


def to_daily(sig, lag_days, idx):
    """weekly signal at week-ending F -> usable from the trade date F + lag_days (its close), held until replaced"""
    x = pd.Series(sig.to_numpy(), index=sig.index + pd.Timedelta(days=lag_days))
    return x.reindex(idx.union(x.index)).ffill().reindex(idx)


def sleeve(root, pos):
    d = F.daily(root); vol = d.r.rolling(60, min_periods=40).std() * np.sqrt(252)
    w = (pos.reindex(d.index).fillna(0.0) * (0.10 / vol).clip(upper=3.0)).fillna(0.0).shift(1).fillna(0.0)
    return w * d.r - w.diff().abs().fillna(w.abs()) * d.cost


g = gas(); idx = F.daily("NG").index
lvl = -(g / norm(g) - 1).div(0.10).clip(-1, 1)
ch = g.diff(); s2 = -np.sign(ch - norm(ch))
p2 = pd.Series(np.nan, index=idx)
for t, v in s2.dropna().items():
    st = t + pd.Timedelta(days=7); k = idx.searchsorted(st)
    p2.iloc[k:k + 5] = v
S = {"T1 NG storage level": sleeve("NG", to_daily(lvl.dropna(), 7, idx)),
     "T2 NG storage surprise": sleeve("NG", p2.fillna(0.0))}
c = petroleum("WCESTUS1w"); S["T3 crude stocks level"] = sleeve("CL", to_daily((-(c / norm(c) - 1).div(0.10).clip(-1, 1)).dropna(), 6, F.daily("CL").index))
gs, di = petroleum("WGTSTUS1w"), petroleum("WDISTUS1w")
S["T4 products level"] = 0.5 * sleeve("RB", to_daily((-(gs / norm(gs) - 1).div(0.10).clip(-1, 1)).dropna(), 6, F.daily("RB").index)) \
    + 0.5 * sleeve("HO", to_daily((-(di / norm(di) - 1).div(0.10).clip(-1, 1)).dropna(), 6, F.daily("HO").index))
base = fbook.sleeves(); ref = [round(F.sharpe(fbook.build(base), *s), 3) for s in F.SPLITS]
out = {"reference": ref, "trials": {}}
entrants = {}
for k, p in S.items():
    a = "2015-01-01" if k.startswith("T1") or k.startswith("T2") else "2010-06-01"
    tune = round(F.sharpe(p, a, "2022-12-31"), 3)
    b = fbook.build(base.assign(**{k: p})); r = [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
    e = bool(tune >= 0.3)
    out["trials"][k] = {"sleeve 2010-17 / 2018-22 / 2023-26": list(F.splits(p)), "tune": tune, "appraisal ES/NQ 2010-22": round(fbook.appraisal(p), 3),
                        "corr with book 2023-26": round(float(pd.concat([p, fbook.build(base)], axis=1).loc["2023":].corr().iloc[0, 1]), 2),
                        "enters": e, "book": r, "pass": bool(e and r[2] >= ref[2] + 0.05 and r[0] >= ref[0] and r[1] >= ref[1])}
    if e:
        entrants[k] = p
    print(k, out["trials"][k], flush=True)
if len(entrants) > 1:
    b = fbook.build(base.assign(**entrants)); out["all entrants together"] = [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
out["passed"] = [k for k, v in out["trials"].items() if v["pass"]]
(ROOT / "results/gen476.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in out if k != "trials"}, indent=1))

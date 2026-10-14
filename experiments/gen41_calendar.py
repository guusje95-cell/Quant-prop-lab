"""Gen41 (config/gen41_protocol.json): index calendar effects (turn-of-month, TOM+trend, pre-holiday, first half-month)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.data import yahoo as Y  # noqa: E402
from qpl.research import factory as F  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402

PROTO = "config/gen41_protocol.json"
IDX = ["US500", "US100", "US30", "US2000", "DE40", "UK100", "JP225", "FR40", "EU50", "AU200", "HK50"]
PER = {"DEV": ("2000-01-01", "2012-12-31"), "VAL": ("2013-01-01", "2019-12-31"), "TEST": ("2020-01-01", "2026-10-13")}
SQ = np.sqrt(252)


def sh(x):
    x = x.dropna(); return float(x.mean() / x.std() * SQ) if len(x) > 30 and x.std() > 0 else 0.0


def masks(c):
    """Position held over the return from close t-1 to close t (position decided at close t-1). Own calendar."""
    d = c.index
    ym = d.year * 12 + d.month
    s = pd.Series(ym, index=d)
    pos_in_month = s.groupby(s).cumcount() + 1                         # 1-based trading-day number
    n_in_month = s.groupby(s).transform("count")
    from_end = n_in_month - pos_in_month                               # 0 = last trading day
    tom = ((from_end == 0) | (pos_in_month <= 3)).astype(float)        # returns on last day and first 3 days
    ma = c.rolling(200, min_periods=200).mean()
    # trend filter evaluated at entry = close of 2nd-to-last day (decision for the next 4 returns)
    entry_ok = (c > ma).where(from_end == 1)
    trend_flag = entry_ok.ffill()
    tom_tr = tom * (trend_flag.shift(1) == True).astype(float)         # noqa: E712
    gap = pd.Series(d, index=d).diff().dt.days.shift(-1)               # calendar days to next trading day
    nextwd = pd.Series(d, index=d).shift(-1)
    weekend_only = (pd.Series(d.dayofweek, index=d) == 4) & (gap == 3)
    pre_hol = ((gap > 1) & ~weekend_only).astype(float).shift(1).fillna(0)   # return of the day AFTER the pre-holiday close? no:
    # pre-holiday effect = return ON the pre-holiday trading day -> position held from close t-1 to close t where t is pre-holiday
    pre_hol = ((gap > 1) & ~weekend_only).astype(float)
    first_half = (pos_in_month <= 10).astype(float)
    return {"A1_TURN_OF_MONTH": tom, "A2_TOM_TREND": tom_tr, "A3_PRE_HOLIDAY": pre_hol, "A4_FIRST_HALF_MONTH": first_half}


def run(cmult=1.0):
    per_idx = {h: {} for h in ("A1_TURN_OF_MONTH", "A2_TOM_TREND", "A3_PRE_HOLIDAY", "A4_FIRST_HALF_MONTH")}
    for n in IDX:
        c = Y.load(n)["close"].dropna(); c = c[c > 0]
        r = c.pct_change()
        r = r.where(r.abs() < 0.25)
        for h, m in masks(c).items():
            pos = m.reindex(r.index).fillna(0)
            entries = pos.diff().abs().fillna(pos)
            net = pos * r.fillna(0) - entries * 2.0 * cmult / 1e4 - pos * 0.03 / 252
            per_idx[h][n] = net
    cal = pd.bdate_range("2000-01-03", "2026-10-13")
    return {h: pd.DataFrame(v).reindex(cal).fillna(0) for h, v in per_idx.items()}


base, stress = run(), run(2.0)
out = {"hyp": {}}; rng = np.random.default_rng(41); pv = {}; series = {}
for h, df in base.items():
    book = df.mean(axis=1)
    k = 0.10 / (book.loc[slice(*PER["DEV"])].std() * SQ)
    x = book * k
    st = {p: round(sh(x.loc[a:z]), 3) for p, (a, z) in PER.items()}
    st["ALL"] = round(sh(x), 3)
    st["TEST_2x"] = round(sh(stress[h].mean(axis=1).loc[slice(*PER["TEST"])]), 3)
    st["per_index_sharpe"] = {n: round(sh(df[n]), 2) for n in IDX}
    st["n_index_positive"] = int(sum(v > 0 for v in st["per_index_sharpe"].values()))
    m = (1 + x).resample("ME").prod() - 1
    st["pos_months"] = round(float((m > 0).mean()), 3); st["worst_month"] = round(float(m.min()), 4)
    eq = (1 + x).cumprod(); st["cagr_at10vol"] = round(float(eq.iloc[-1] ** (252 / len(x)) - 1), 4)
    st["max_dd_at10vol"] = round(float((eq / eq.cummax() - 1).min()), 4)
    st["exposure_share"] = round(float((df != 0).mean().mean()), 3)
    xv = x.to_numpy(); bi = T.stationary_bootstrap_indices(len(xv), 5000, 10.0, rng)
    pv[h] = float(np.mean((xv - xv.mean())[bi].mean(axis=1) >= xv.mean())); st["p_raw"] = round(pv[h], 4)
    out["hyp"][h] = st; series[h] = x
order = sorted(pv, key=pv.get); r_ = 0.0
for i, h in enumerate(order):
    r_ = max(r_, min(1.0, (len(order) - i) * pv[h])); out["hyp"][h]["p_holm"] = round(r_, 4)
for h, st in out["hyp"].items():
    st["ACCEPTED"] = bool(st["DEV"] >= 0.4 and st["VAL"] >= 0.3 and st["TEST"] >= 0.3 and st["TEST_2x"] >= 0.2 and st["p_holm"] < 0.05
                          and st["n_index_positive"] >= 8)
    F.append({"kind": "holdout_evaluation", "hypothesis_id": f"GEN41_{h}", "protocol": PROTO, "result": {k: v for k, v in st.items() if k != "per_index_sharpe"}})
out["accepted"] = [h for h, s in out["hyp"].items() if s["ACCEPTED"]]
(ROOT / "results/gen41_calendar.json").write_text(json.dumps(out, indent=1, default=float))
pd.to_pickle(series, ROOT / "results/gen41_series.pkl")
for h, s in out["hyp"].items():
    print(h, {k: v for k, v in s.items() if k != "per_index_sharpe"}); print("   ", s["per_index_sharpe"])
print("ACCEPTED", out["accepted"])

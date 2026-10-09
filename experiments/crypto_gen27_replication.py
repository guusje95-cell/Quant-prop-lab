"""Gen27 part A (config/crypto_gen27_protocol.json): the 4 frozen gen26 finalists on the untouched universe U2
(point-in-time market-cap ranks 11-30), 2018-01-01 .. 2026-05-23, 15 bp/turnover, 2x stress."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.data import coinmetrics as CM  # noqa: E402
from qpl.research import factory as F  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import crypto_zoo as Z  # noqa: E402

PROTO = "config/crypto_gen27_protocol.json"
COST, FUND = 15.0, 3e-4
A, Zd = "2018-01-01", "2026-05-23"
SQ = np.sqrt(365)

CMP = CM.load()
px = CMP["PriceUSD"].loc["2016-01-01":].drop(columns=["avaxp", "avaxx"], errors="ignore")
cap = CMP["CapMrktCurUSD"].reindex_like(px)
ret = px.pct_change(fill_method=None)
hist = px.notna().cumsum() >= 200
rank = cap.where(hist & px.notna()).rank(axis=1, ascending=False)
member = (rank > 10) & (rank <= 30)
vol = np.log(px).diff().rolling(30, min_periods=20).std() * SQ


def sh(x):
    x = x.dropna(); return float(x.mean() / x.std() * SQ) if len(x) > 30 and x.std() > 0 else 0.0


def engine(sigs, cmult=1.0):
    w = (sigs.reindex_like(px).fillna(0) * (0.40 / vol)).clip(-1, 1).where(member, 0.0)
    w = w.div(member.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    gross = (w.shift(1) * ret.fillna(0)).sum(axis=1)
    cost = w.diff().abs().sum(axis=1).fillna(0) * COST * cmult / 1e4
    fund = (w.shift(1) * FUND).sum(axis=1)
    return pd.DataFrame({"gross": gross, "net": gross - cost - fund, "cost": cost, "turnover": w.diff().abs().sum(axis=1)}).loc[A:Zd]


def per_asset(fn, mode):
    return pd.DataFrame({a: Z.apply_mode(fn(px[a].dropna()), mode) for a in px.columns if px[a].notna().sum() > 250})


RULES = {"R1_SHORT_BREAKOUT_7_2_LO": (lambda c: Z.short_breakout(c, 7, 2), "LO"),
         "R2_RSI_MOMENTUM_14_LO": (lambda c: Z.rsi_momentum(c, 14, 55, 45), "LO"),
         "R3_TSMOM_30_LS": (lambda c: Z.tsmom(c, 30), "LS"),
         "R4_TSMOM_30_LO": (lambda c: Z.tsmom(c, 30), "LO")}

BH = engine(pd.DataFrame(1.0, index=px.index, columns=px.columns))["net"]
out = {"U2_members_per_year": member.loc[A:Zd].sum(axis=1).resample("YE").mean().round(1).rename(lambda t: t.year).to_dict(),
       "U2_bh_sharpe": round(sh(BH), 3)}
rng = np.random.default_rng(27)
pvals = {}
for name, (fn, mode) in RULES.items():
    sig = per_asset(fn, mode)
    d1, d2 = engine(sig), engine(sig, 2.0)
    x = d1["net"]
    beta = float(np.cov(x, BH)[0, 1] / BH.var()); resid = x - beta * BH
    yrs = {int(y): round(sh(g), 2) for y, g in x.groupby(x.index.year)}
    full = [yrs[y] for y in range(2018, 2026)]
    eq = (1 + x).cumprod()
    xv = x.to_numpy(); idx = T.stationary_bootstrap_indices(len(xv), 5000, 10.0, rng)
    boot = (xv - xv.mean())[idx].mean(axis=1)
    pvals[name] = float(np.mean(boot >= xv.mean()))
    out[name] = {"net_sharpe": round(sh(x), 3), "gross_sharpe": round(sh(d1["gross"]), 3), "net_sharpe_2x": round(sh(d2["net"]), 3),
                 "resid_sharpe": round(sh(resid), 3), "beta": round(beta, 3),
                 "cagr": round(float(eq.iloc[-1] ** (365 / len(x)) - 1), 4), "ann_vol": round(float(x.std() * SQ), 4),
                 "max_dd": round(float((eq / eq.cummax() - 1).min()), 4), "turnover_per_yr": round(float(d1["turnover"].mean() * 365), 2),
                 "by_year": yrs, "years_positive_2018_2025": int(sum(v > 0 for v in full)),
                 "sub_2018_2021": round(sh(x.loc[:"2021"]), 3), "sub_2022_2026": round(sh(x.loc["2022":]), 3),
                 "boot_p_one_sided": pvals[name]}
# Holm across the 4 rules
order = sorted(pvals, key=pvals.get); m = len(order); adj = {}; run = 0.0
for i, k in enumerate(order):
    run = max(run, min(1.0, (m - i) * pvals[k])); adj[k] = run
for name in RULES:
    r = out[name]; r["holm_p"] = round(adj[name], 4)
    r["gate_A"] = bool(r["net_sharpe"] >= 0.5 and r["net_sharpe_2x"] >= 0.3 and r["years_positive_2018_2025"] >= 5
                       and r["resid_sharpe"] >= 0.3 and r["holm_p"] < 0.05)
    F.append({"kind": "holdout_evaluation", "hypothesis_id": f"GEN27A_{name}", "protocol": PROTO,
              "result": {k: r[k] for k in ("net_sharpe", "net_sharpe_2x", "resid_sharpe", "years_positive_2018_2025", "holm_p", "gate_A")}})
    print(name, json.dumps({k: v for k, v in r.items() if k != "by_year"}), r["by_year"], flush=True)
(ROOT / "results/crypto_gen27_replication.json").write_text(json.dumps(out, indent=1, default=str))
print("U2 B&H Sharpe", out["U2_bh_sharpe"])

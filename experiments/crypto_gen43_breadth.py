"""Gen43 (config/crypto_gen43_protocol.json): E2 + O3 on point-in-time top-10 vs top-20 vs top-30 (Coin Metrics, close-only)."""
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
from qpl.strategies import cft_e2 as E  # noqa: E402

PROTO = "config/crypto_gen43_protocol.json"
PER = {"DEV": ("2018-01-01", "2021-12-31"), "VAL": ("2022-01-01", "2023-12-31"), "TEST": ("2024-01-01", "2026-05-24")}
SQ = np.sqrt(365); END = "2026-05-24"
CMP = CM.load()
px = CMP["PriceUSD"].loc["2016-01-01":END].drop(columns=["avaxp", "avaxx"], errors="ignore")
cap = CMP["CapMrktCurUSD"].reindex_like(px)
hist = px.notna().cumsum() >= 200
rank = cap.where(hist & px.notna()).rank(axis=1, ascending=False)
vol = np.log(px).diff().rolling(30, min_periods=20).std() * SQ
ret = px.pct_change(fill_method=None).fillna(0)
sig = pd.DataFrame({a: E.signal_one(px[a]) for a in px.columns if px[a].notna().sum() > 250}).reindex_like(px).fillna(0)


def cmcap(a):
    return pd.read_csv(CM.SRC / f"{a}.csv", usecols=["time", "CapMrktCurUSD"], parse_dates=["time"]).set_index("time")["CapMrktCurUSD"]


stab = cmcap("usdt").fillna(0) + cmcap("usdc").reindex(cmcap("usdt").index).fillna(0)
f3 = E.stable_overlay(stab, px.index)


def book(top, cmult=1.0):
    member = rank <= top
    w = (sig.mul(f3, axis=0) * (0.40 / vol).clip(upper=1.0)).where(member, 0.0)
    w = w.div(member.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    wp = w.shift(1).fillna(0)
    bp = pd.DataFrame(np.where(rank.shift(1) <= 10, 7.5, 15.0), index=px.index, columns=px.columns)
    cost = (wp.diff().abs() * bp).sum(axis=1).fillna(0) * cmult / 1e4
    return pd.DataFrame({"net": (wp * ret).sum(axis=1) - cost, "gexp": wp.abs().sum(axis=1)}).loc["2018-01-01":END]


def sh(x):
    x = x.dropna(); return float(x.mean() / x.std() * SQ) if len(x) > 30 and x.std() > 0 else 0.0


def stats(x):
    m = (1 + x).resample("ME").prod() - 1; eq = (1 + x).cumprod()
    return {**{p: round(sh(x.loc[a:z]), 3) for p, (a, z) in PER.items()}, "ALL": round(sh(x), 3), "pos_months": round(float((m > 0).mean()), 3),
            "median_month": round(float(m.median()), 4), "worst_month": round(float(m.min()), 4), "max_dd": round(float((eq / eq.cummax() - 1).min()), 4)}


B = book(10)["net"]
out = {"BASE_TOP10": stats(B)}; rng = np.random.default_rng(43); pv = {}
for name, top in (("BROAD_TOP20", 20), ("BROAD_TOP30", 30)):
    d = book(top)["net"]; d2 = book(top, 2.0)["net"]
    k = B.std() / d.std(); x = d * k
    st = stats(x); st["TEST_2x"] = round(sh(d2.loc[slice(*PER["TEST"])]), 3)
    st["beats_each_period"] = bool(all(st[p] > out["BASE_TOP10"][p] for p in PER))
    st["pos_months_ge_base"] = bool(st["pos_months"] >= out["BASE_TOP10"]["pos_months"])
    dl = (x - B).to_numpy(); bi = T.stationary_bootstrap_indices(len(dl), 5000, 20.0, rng)
    pv[name] = float(np.mean((dl - dl.mean())[bi].mean(axis=1) >= dl.mean())); st["p_raw"] = round(pv[name], 4)
    out[name] = st
order = sorted(pv, key=pv.get); r_ = 0.0
for i, n in enumerate(order):
    r_ = max(r_, min(1.0, (len(order) - i) * pv[n])); out[n]["p_holm"] = round(r_, 4)
for n in pv:
    s = out[n]; s["ACCEPTED"] = bool(s["beats_each_period"] and s["pos_months_ge_base"] and s["TEST_2x"] >= 0.8 and s["p_holm"] < 0.05)
    F.append({"kind": "holdout_evaluation", "hypothesis_id": f"GEN43_{n}", "protocol": PROTO, "result": s})
(ROOT / "results/crypto_gen43_breadth.json").write_text(json.dumps(out, indent=1, default=float))
for k_, v in out.items():
    print(k_, v)

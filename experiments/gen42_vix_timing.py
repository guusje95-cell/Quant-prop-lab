"""Gen42 (config/gen42_protocol.json): VIX-term-structure / trend timed index exposure on US500/US100 (+ replications)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.data import yahoo as Y  # noqa: E402
from qpl.prop_simulation import cft_daily as CFT  # noqa: E402
from qpl.research import factory as F  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402

PROTO = "config/gen42_protocol.json"
PER = {"DEV": ("2007-01-01", "2013-12-31"), "VAL": ("2014-01-01", "2019-12-31"), "TEST": ("2020-01-01", "2026-10-13")}
SQ = np.sqrt(252)
vix = Y.load("VIX")["close"]; vix3 = Y.load("VIX3M")["close"]
ts = (vix / vix3).dropna()


def sh(x):
    x = x.dropna(); return float(x.mean() / x.std() * SQ) if len(x) > 30 and x.std() > 0 else 0.0


def index_series(name, europe=False, cmult=1.0):
    d = Y.load(name); c = d["close"].dropna(); c = c[c > 0]
    r = c.pct_change().where(lambda z: z.abs() < 0.25)
    lo = (d["low"] / c.shift(1) - 1).reindex(c.index); hi = (d["high"] / c.shift(1) - 1).reindex(c.index)
    sig_ts = ts.reindex(c.index, method="ffill")
    if europe:
        sig_ts = ts.shift(1).reindex(c.index, method="ffill")      # US close t not known at European close t
    ma = c.rolling(200, min_periods=200).mean()
    vol = r.rolling(20, min_periods=15).std() * SQ
    pos = {"B0": pd.Series(1.0, index=c.index),
           "B1_VIX_TS": (sig_ts < 1.0).astype(float),
           "B2_TREND200": (c > ma).astype(float),
           "B3_VIX_TS_AND_TREND": ((sig_ts < 1.0) & (c > ma)).astype(float),
           "B4_VIX_TS_VOLMANAGED": (sig_ts < 1.0).astype(float) * (0.15 / vol).clip(upper=1.5)}
    out = {}
    for k, p in pos.items():
        p = p.where(c.index >= pd.Timestamp("2006-07-17"), np.nan).fillna(0) if k != "B0" else p
        w = p.shift(1).fillna(0)                                    # decided at close t-1
        cost = w.diff().abs().fillna(0) * 2.0 * cmult / 1e4 + w * 0.03 * cmult / 252
        net = w * r.fillna(0) - cost
        worst = w * lo.fillna(0).clip(upper=0) - cost
        best = w * hi.fillna(0).clip(lower=0) - cost
        out[k] = pd.DataFrame({"net": net, "worst": worst, "best": best, "exp": w})
    return out


cal = pd.bdate_range("2007-01-01", "2026-10-13")
U = {n: index_series(n) for n in ("US500", "US100")}
Us = {n: index_series(n, cmult=2.0) for n in ("US500", "US100")}
REPL = {"US30": False, "US2000": False, "DE40": True, "UK100": True}
R = {n: index_series(n, europe=e) for n, e in REPL.items()}


def book(d, key):
    return sum(d[n][key].reindex(cal).fillna(0) for n in d) / len(d)


out = {"hyp": {}}
B0 = book(U, "B0")
b0 = {p: round(sh(B0["net"].loc[a:z]), 3) for p, (a, z) in PER.items()}; b0["ALL"] = round(sh(B0["net"]), 3)
out["B0"] = b0
rng = np.random.default_rng(42); pv = {}; series = {}
for h in ("B1_VIX_TS", "B2_TREND200", "B3_VIX_TS_AND_TREND", "B4_VIX_TS_VOLMANAGED"):
    d = book(U, h); ds = book(Us, h)
    st = {p: round(sh(d["net"].loc[a:z]), 3) for p, (a, z) in PER.items()}; st["ALL"] = round(sh(d["net"]), 3)
    st["TEST_2x"] = round(sh(ds["net"].loc[slice(*PER["TEST"])]), 3)
    st["beats_B0_each_period"] = bool(all(st[p] > b0[p] for p in PER))
    st["avg_exposure"] = round(float(d["exp"].mean()), 3)
    eq = (1 + d["net"]).cumprod(); st["cagr"] = round(float(eq.iloc[-1] ** (252 / len(eq)) - 1), 4)
    st["max_dd"] = round(float((eq / eq.cummax() - 1).min()), 4); st["worst_day"] = round(float(d["worst"].min()), 4)
    m = (1 + d["net"]).resample("ME").prod() - 1
    st["pos_months"] = round(float((m > 0).mean()), 3); st["worst_month"] = round(float(m.min()), 4)
    a, b = d["net"], B0["net"]
    dl = (a * (b.std() / a.std()) - b).to_numpy(); bi = T.stationary_bootstrap_indices(len(dl), 5000, 20.0, rng)
    pv[h] = float(np.mean((dl - dl.mean())[bi].mean(axis=1) >= dl.mean())); st["p_raw"] = round(pv[h], 4)
    st["replication_beats_B0"] = {n: bool(sh(R[n][h]["net"]) > sh(R[n]["B0"]["net"])) for n in REPL}
    st["replication_sharpes"] = {n: [round(sh(R[n][h]["net"]), 2), round(sh(R[n]["B0"]["net"]), 2)] for n in REPL}
    out["hyp"][h] = st; series[h] = d
order = sorted(pv, key=pv.get); r_ = 0.0
for i, h in enumerate(order):
    r_ = max(r_, min(1.0, (len(order) - i) * pv[h])); out["hyp"][h]["p_holm"] = round(r_, 4)
for h, st in out["hyp"].items():
    st["ACCEPTED"] = bool(all(st[p] >= 0.6 for p in PER) and st["beats_B0_each_period"] and st["TEST_2x"] >= 0.5 and st["p_holm"] < 0.05
                          and sum(st["replication_beats_B0"].values()) >= 3)
    F.append({"kind": "holdout_evaluation", "hypothesis_id": f"GEN42_{h}", "protocol": PROTO, "result": {k: v for k, v in st.items()}})
out["accepted"] = [h for h, s in out["hyp"].items() if s["ACCEPTED"]]
(ROOT / "results/gen42_vix_timing.json").write_text(json.dumps(out, indent=1, default=str))
pd.to_pickle(series, ROOT / "results/gen42_series.pkl")
print("B0", b0)
for h, s in out["hyp"].items():
    print(h, s)
print("ACCEPTED", out["accepted"])

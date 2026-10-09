"""Gen35 (config/crypto_gen35_protocol.json): frozen E2 on macro assets (MX) + E2 LIQUID2 crypto (CX), one MT5-route account."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.data import macro_daily as MD, static_klines as SK  # noqa: E402
from qpl.prop_simulation import cft_daily as CFT  # noqa: E402
from qpl.research import factory as F  # noqa: E402
from qpl.strategies import cft_e2 as E, crypto_zoo as Z  # noqa: E402

PROTO = "config/crypto_gen35_protocol.json"
SQ = np.sqrt(365)
MACRO = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCAD", "USDCHF", "WTI", "BRENT", "SPX"]
COSTS = {**{k: (1.0, 0.02) for k in MACRO[:7]}, "WTI": (3.0, 0.03), "BRENT": (3.0, 0.03), "SPX": (3.0, 0.03)}
P_PER = {"DEV": ("2018-01-01", "2021-12-31"), "VAL": ("2022-01-01", "2023-12-31"), "TEST": ("2024-01-01", "2026-10-08")}
M_PER = {"DEV": ("1990-01-01", "2009-12-31"), "VAL": ("2010-01-01", "2017-12-31"), "TEST": ("2018-01-01", "2026-10-08")}


def sh(x):
    x = x.dropna(); return float(x.mean() / x.std() * SQ) if len(x) > 30 and x.std() > 0 else 0.0


def e2_ls(s):
    s = s.dropna()
    bo = sum(Z.short_breakout(s, n, k) for n, k in E.BO) / len(E.BO)
    tm = sum(Z.tsmom(s, n) for n in E.TM) / len(E.TM)
    return 0.5 * bo + 0.5 * tm


# ---------------------------------------------------------------- macro sleeve on a calendar-day index
m = MD.load()[MACRO].loc["1985-01-01":"2026-10-08"]
cal = pd.date_range("1986-01-01", "2026-10-08", freq="D")
W, R, SIG = {}, {}, {}
for a in MACRO:
    s = m[a].dropna()
    s = s[s.index >= "1986-01-01"]
    lr = np.log(s).diff()
    vol = lr.rolling(30, min_periods=20).std() * np.sqrt(252)
    sig = e2_ls(s)
    w = (sig * (0.10 / vol).clip(upper=4.0)).where(np.arange(len(s)) >= 200, 0.0).fillna(0)
    W[a] = w.reindex(cal).ffill().fillna(0)                      # position held over weekends / holidays
    R[a] = s.pct_change().reindex(cal).fillna(0)                 # return booked on the asset's trading day
    SIG[a] = (lr.rolling(30, min_periods=20).std()).reindex(cal).ffill()
W, R, DSIG = pd.DataFrame(W), pd.DataFrame(R), pd.DataFrame(SIG)
live = pd.DataFrame({a: pd.Series(1.0, index=m[a].dropna().index).reindex(cal).ffill(limit=5).notna() for a in MACRO})
live["SPX"] &= cal <= pd.Timestamp("2026-02-11")
W = W.where(live, 0.0)
n = live.sum(axis=1).clip(lower=1)
W = W.div(n, axis=0)


def macro_engine(cmult=1.0, smult=1.0):
    wp = W.shift(1).fillna(0)
    turn = wp.diff().abs().fillna(0)
    cost = sum(turn[a] * COSTS[a][0] * cmult / 1e4 + wp[a].abs() * COSTS[a][1] * smult / 365 for a in MACRO)
    gross = (wp * R).sum(axis=1)
    adverse = np.where(np.sign(R) * np.sign(wp) < 0, 2.0 * R.abs(), 0.5 * DSIG.fillna(0)) * (wp.abs() > 0)
    favour = np.where(np.sign(R) * np.sign(wp) > 0, 2.0 * R.abs(), 0.5 * DSIG.fillna(0)) * (wp.abs() > 0)
    worst = -(pd.DataFrame(adverse, index=cal, columns=MACRO) * wp.abs()).sum(axis=1) - cost
    best = (pd.DataFrame(favour, index=cal, columns=MACRO) * wp.abs()).sum(axis=1) - cost
    return pd.DataFrame({"net": gross - cost, "gross": gross, "worst": worst, "best": best, "cost": cost, "gross_exp": wp.abs().sum(axis=1)})


# ---------------------------------------------------------------- crypto sleeve (MT5 CFD costs)
D = SK.load("1d"); c = D["close"].loc["2017-08-17":"2026-10-08", ["BTC", "ETH"]]
h, l = D["high"].reindex_like(c), D["low"].reindex_like(c)
wc = E.raw_weights(c)


def crypto_engine(cmult=1.0, smult=1.0):
    wp = wc.shift(1).fillna(0)
    cost = wp.diff().abs().sum(axis=1).fillna(0) * 8.25 * cmult / 1e4 + wp.abs().sum(axis=1) * 0.20 * smult / 365
    ret = c.pct_change(fill_method=None).fillna(0)
    gross = (wp * ret).sum(axis=1)
    lo, hi = (l / c.shift(1) - 1).fillna(0), (h / c.shift(1) - 1).fillna(0)
    return pd.DataFrame({"net": gross - cost, "gross": gross, "worst": (wp * lo).sum(axis=1) - cost, "best": (wp * hi).sum(axis=1) - cost,
                         "cost": cost, "gross_exp": wp.abs().sum(axis=1)})


def stats(x, worst=None):
    x = x.dropna(); eq = (1 + x).cumprod()
    o = {"sharpe": round(sh(x), 3), "cagr": round(float(eq.iloc[-1] ** (365 / len(x)) - 1), 4), "vol": round(float(x.std() * SQ), 4),
         "max_dd": round(float((eq / eq.cummax() - 1).min()), 4)}
    if worst is not None:
        o["worst_day"] = round(float(worst.loc[x.index].min()), 4)
    return o


def build(cmult=1.0, smult=1.0):
    mx, cx = macro_engine(cmult, smult), crypto_engine(cmult, smult)
    return mx, cx


mx, cx = build()
out = {"MX": {p: stats(mx["net"].loc[a:z]) for p, (a, z) in M_PER.items()}, "CX_mt5": {p: stats(cx["net"].loc[a:z]) for p, (a, z) in P_PER.items()}}
out["MX"]["by_asset_TEST_sharpe"] = {}
for a in MACRO:
    wp = W[a].shift(1).fillna(0); out["MX"]["by_asset_TEST_sharpe"][a] = round(sh((wp * R[a]).loc["2018":]), 2)
idx = pd.date_range("2018-01-01", "2026-10-08", freq="D")
km = 0.10 / (mx["net"].loc["2018":"2021"].std() * SQ); kc = 0.10 / (cx["net"].loc["2018":"2021"].std() * SQ)


def portfolio(mx, cx):
    p = mx.reindex(idx).fillna(0) * km + cx.reindex(idx).fillna(0) * kc
    return p


P1 = portfolio(mx, cx)
out["corr_MX_CX_2018_2026"] = round(float(pd.concat([mx["net"], cx["net"]], axis=1).loc["2018":].corr().iloc[0, 1]), 3)
base_vol = float(P1["net"].loc["2018":"2021"].std() * SQ)
choice = None
for v in (0.08, 0.10, 0.12, 0.14, 0.16):
    Pv = P1 * (v / base_vol); dev = Pv.loc["2018":"2021"]
    eq = (1 + dev["net"]).cumprod()
    ok = dev["worst"].min() > -0.04 and (eq / eq.cummax() - 1).min() > -0.09
    out.setdefault("risk_grid_DEV", {})[v] = {"worst": round(float(dev["worst"].min()), 4), "maxdd": round(float((eq / eq.cummax() - 1).min()), 4), "ok": bool(ok)}
    if ok:
        choice = v
out["chosen_v"] = choice
if choice:
    P = P1 * (choice / base_vol)
    out["P"] = {p: stats(P["net"].loc[a:z], P["worst"]) for p, (a, z) in P_PER.items()}
    out["P"]["ALL"] = stats(P["net"], P["worst"])
    out["P"]["by_year"] = {int(y): round(float((1 + g).prod() - 1), 4) for y, g in P["net"].groupby(P["net"].index.year)}
    out["P"]["avg_gross_exposure"] = {"crypto": round(float((cx["gross_exp"].reindex(idx).fillna(0) * kc * choice / base_vol).mean()), 3),
                                      "macro": round(float((mx["gross_exp"].reindex(idx).fillna(0) * km * choice / base_vol).mean()), 3)}
    mxs, cxs = build(2.0, 2.0)
    Ps = portfolio(mxs, cxs) * (choice / base_vol)
    out["P_stress"] = stats(Ps["net"], Ps["worst"])
    r = P["net"].to_numpy(); lo = P["worst"].to_numpy(); hi = P["best"].to_numpy()
    st = [i for i in range(0, len(idx), 2) if pd.Timestamp("2023-01-01") <= idx[i] <= pd.Timestamp("2024-06-30")]
    out["CFT_2PHASE_TEST"] = CFT.summarize([CFT.simulate_start(r, s, "2PHASE", mode="optimistic", max_days=548, lo=lo, hi=hi) for s in st])
    out["CFT_1PHASE_TEST"] = CFT.summarize([CFT.simulate_start(r, s, "1PHASE", mode="optimistic", max_days=548, lo=lo, hi=hi) for s in st])
    g = out
    gates = {"T1": g["MX"]["VAL"]["sharpe"] >= 0.3 and g["MX"]["TEST"]["sharpe"] >= 0.3,
             "T2": g["P"]["ALL"]["sharpe"] >= 1.3 and all(g["P"][p]["sharpe"] >= 1.0 for p in P_PER),
             "T3": g["P"]["ALL"]["cagr"] >= 0.15 and g["P"]["TEST"]["cagr"] >= 0.12,
             "T4": g["P"]["ALL"]["worst_day"] > -0.05 and g["P"]["ALL"]["max_dd"] > -0.10,
             "T5": g["P_stress"]["sharpe"] >= 1.0,
             "T6": g["CFT_2PHASE_TEST"]["P_pass"] >= 0.60 and g["CFT_2PHASE_TEST"]["P_fail_daily"] <= 0.10}
    out["gates"] = {k: bool(v) for k, v in gates.items()}; out["TARGET_MET"] = all(gates.values())
    P.to_pickle(ROOT / "results/crypto_gen35_P.pkl")
F.append({"kind": "holdout_evaluation", "hypothesis_id": "GEN35_CROSSASSET_MT5", "protocol": PROTO,
          "result": {k: out.get(k) for k in ("chosen_v", "gates", "TARGET_MET")}})
(ROOT / "results/crypto_gen35_crossasset.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str))

"""Gen40 (config/gen40_protocol.json): multi-asset EWMAC trend on MT5 CFD markets (Yahoo daily) + combination with C*."""
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

PROTO = "config/gen40_protocol.json"
GROUPS = {"FX": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "EURCHF"],
          "IDX": ["US500", "US100", "US30", "US2000", "DE40", "UK100", "JP225", "FR40", "EU50", "AU200", "HK50"],
          "CMD": ["GOLD", "SILVER", "WTI", "BRENT", "COPPER"]}
BONDS = ["UST10Y", "UST20Y"]
COST_BP = {**{k: 1.0 for k in GROUPS["FX"]}, **{k: 2.0 for k in GROUPS["IDX"]}, "GOLD": 3.0, "SILVER": 3.0, "WTI": 4.0, "BRENT": 4.0, "COPPER": 4.0,
           "UST10Y": 2.0, "UST20Y": 2.0}
FIN = {**{k: 0.015 for k in GROUPS["FX"]}, **{k: 0.03 for k in GROUPS["IDX"] + GROUPS["CMD"] + BONDS}}
PER = {"DEV": ("2004-01-01", "2013-12-31"), "VAL": ("2014-01-01", "2019-12-31"), "TEST": ("2020-01-01", "2026-10-13")}
SPEEDS = [(8, 32), (16, 64), (32, 128), (64, 256)]
SQ = np.sqrt(252)


def sh(x, ann=SQ):
    x = x.dropna(); return float(x.mean() / x.std() * ann) if len(x) > 30 and x.std() > 0 else 0.0


def load(names):
    C, H, L = {}, {}, {}
    for n in names:
        d = Y.load(n)
        adj = (d["adjclose"] / d["close"]).where(d["close"] > 0)
        C[n], H[n], L[n] = d["adjclose"], d["high"] * adj, d["low"] * adj
    idx = pd.bdate_range("2000-01-03", "2026-10-13")
    f = lambda D: pd.DataFrame(D).reindex(idx)
    return f(C), f(H), f(L)


def forecast(c):
    c = c.dropna()
    sd = c.pct_change().ewm(span=36, min_periods=30).std()
    fs = []
    for a, b in SPEEDS:
        raw = (c.ewm(span=a, min_periods=a).mean() - c.ewm(span=b, min_periods=b).mean()) / (c * sd)
        scale = raw.abs().expanding(min_periods=250).mean()
        fs.append((raw / scale).clip(-2, 2))
    return (sum(fs) / len(fs)).clip(-2, 2)


def book(groups, C, H, L, cmult=1.0, fmult=1.0):
    names = [n for g in groups.values() for n in g]
    ret = C.pct_change(fill_method=None)
    W = pd.DataFrame(0.0, index=C.index, columns=names)
    for g, members in groups.items():
        for n in members:
            c = C[n]
            fc = forecast(c).reindex(C.index).ffill(limit=5)
            vol = c.dropna().pct_change().ewm(span=36, min_periods=30).std().reindex(C.index).ffill(limit=5) * SQ
            W[n] = (fc * (0.10 / vol) / len(members) / len(groups)).fillna(0)
    # buffering: hold unless target deviates by > 10% of target
    held = W.copy() * 0; prev = np.zeros(len(names)); arr = W.to_numpy(); out = np.zeros_like(arr)
    for t in range(len(arr)):
        tgt = arr[t]; move = np.abs(tgt - prev) > 0.1 * np.abs(tgt)
        prev = np.where(move, tgt, prev); out[t] = prev
    W = pd.DataFrame(out, index=W.index, columns=names)
    wp = W.shift(1).fillna(0)
    turn = wp.diff().abs().fillna(0)
    cost = sum(turn[n] * COST_BP[n] * cmult / 1e4 + wp[n].abs() * FIN[n] * fmult / 252 for n in names)
    r = ret[names].fillna(0)
    gross = (wp * r).sum(axis=1)
    lo, hi = (L[names] / C[names].shift(1) - 1).fillna(0), (H[names] / C[names].shift(1) - 1).fillna(0)
    worst = (wp.clip(lower=0) * lo + wp.clip(upper=0) * hi).sum(axis=1) - cost
    best = (wp.clip(lower=0) * hi + wp.clip(upper=0) * lo).sum(axis=1) - cost
    grp = {g: (wp[m] * r[m]).sum(axis=1) for g, m in groups.items()}
    d = pd.DataFrame({"gross": gross, "net": gross - cost, "worst": worst, "best": best, "cost": cost, "gexp": wp.abs().sum(axis=1), **grp})
    return d.loc["2004-01-01":]


C, H, L = load([n for g in GROUPS.values() for n in g] + BONDS)
TF = book(GROUPS, C, H, L)
TFs = book(GROUPS, C, H, L, 2.0, 2.0)
TFb = book({**GROUPS, "BOND": BONDS}, C, H, L)
k = 0.10 / (TF["net"].loc[slice(*PER["DEV"])].std() * SQ)
out = {"TF1": {p: round(sh(TF["net"].loc[a:z]), 3) for p, (a, z) in PER.items()}}
out["TF1"]["ALL"] = round(sh(TF["net"]), 3); out["TF1"]["gross_ALL"] = round(sh(TF["gross"]), 3)
out["TF1"]["TEST_stress"] = round(sh(TFs["net"].loc[slice(*PER["TEST"])]), 3)
out["TF1"]["by_group_sharpe_2004_2026"] = {g: round(sh(TF[g]), 3) for g in GROUPS}
out["TF1"]["by_year"] = {int(y): round(sh(g), 2) for y, g in TF["net"].groupby(TF.index.year)}
x = TF["net"] * k; eq = (1 + x).cumprod()
out["TF1"]["at10vol"] = {"cagr": round(float(eq.iloc[-1] ** (252 / len(x)) - 1), 4), "max_dd": round(float((eq / eq.cummax() - 1).min()), 4),
                         "worst_day": round(float((TF["worst"] * k).min()), 4), "cost_pa": round(float((TF["cost"] * k).mean() * 252), 4)}
m = (1 + x).resample("ME").prod() - 1
out["TF1"]["pos_months"] = round(float((m > 0).mean()), 3)
out["TF1_BONDS_variant"] = {p: round(sh(TFb["net"].loc[a:z]), 3) for p, (a, z) in PER.items()}

# combination with C* (calendar days)
Cs = pd.read_pickle(ROOT / "results/crypto_gen38_Cstar_series.pkl")
cal = pd.date_range("2018-01-01", "2026-10-08")
tfc = (TF[["net", "worst", "best"]] * k).reindex(cal).fillna(0)
cs = Cs[["net", "worst", "best"]].reindex(cal).fillna(0)
kc = 0.10 / (cs["net"].loc["2018":"2021"].std() * np.sqrt(365)); kt = 0.10 / (tfc["net"].loc["2018":"2021"].std() * np.sqrt(365))
combo = cs * kc + tfc * kt
out["corr_TF1_Cstar"] = round(float(pd.concat([tfc["net"], cs["net"]], axis=1).corr().iloc[0, 1]), 3)


def mstats(d, scale_vol=0.12):
    s = scale_vol / (d["net"].std() * np.sqrt(365)); x = d["net"] * s; eq = (1 + x).cumprod()
    mm = (1 + x).resample("ME").prod() - 1; yr = (1 + x).resample("YE").prod() - 1
    neg = (mm <= 0).astype(int); run = best = 0
    for v in neg: run = run + 1 if v else 0; best = max(best, run)
    return {"sharpe": round(sh(d["net"], np.sqrt(365)), 3), "cagr_at12vol": round(float(eq.iloc[-1] ** (365 / len(x)) - 1), 4),
            "max_dd": round(float((eq / eq.cummax() - 1).min()), 4), "worst_day": round(float((d["worst"] * s).min()), 4),
            "pos_months": round(float((mm > 0).mean()), 3), "median_month": round(float(mm.median()), 4), "worst_month": round(float(mm.min()), 4),
            "longest_losing_streak_m": int(best), "years": {int(i.year): round(float(v), 4) for i, v in yr.items()}}


out["Cstar_alone_2018_2026"] = mstats(cs)
out["TF1_alone_2018_2026"] = mstats(tfc)
out["COMBO_2018_2026"] = mstats(combo)
cb, ca = out["COMBO_2018_2026"], out["Cstar_alone_2018_2026"]
g = out["TF1"]
gates = {"TF_DEV": g["DEV"] >= 0.4, "TF_VAL": g["VAL"] >= 0.3, "TF_TEST": g["TEST"] >= 0.3, "TF_stress": g["TEST_stress"] >= 0.2,
         "corr": abs(out["corr_TF1_Cstar"]) < 0.3, "groups_same_sign": all(v > 0 for v in g["by_group_sharpe_2004_2026"].values())}
out["gates_TF1"] = {k_: bool(v) for k_, v in gates.items()}
out["TF1_PASS"] = all(gates.values())
out["COMBO_BETTER_CONSISTENCY"] = bool(cb["pos_months"] >= 0.55 and cb["sharpe"] >= ca["sharpe"] - 0.1
                                       and all(v >= -0.05 for y, v in cb["years"].items() if 2018 <= y <= 2025))
# prop: TF1 alone on generic MT5 2-Phase (5% daily equity, 10% static)
r = x.to_numpy(); lo = (TF["worst"] * k).to_numpy(); hi = (TF["best"] * k).to_numpy(); idx = x.index
grid = {}
for v in (0.08, 0.10, 0.12, 0.15, 0.20):
    s = v / 0.10
    for tag, (a, z) in (("SEL", ("2004-01-01", "2019-06-30")), ("TEST", ("2020-01-01", "2025-04-30"))):
        st = [i for i in range(0, len(idx), 3) if pd.Timestamp(a) <= idx[i] <= pd.Timestamp(z)]
        grid[f"{v}|{tag}"] = CFT.summarize([CFT.simulate_start(r * s, i, "2PHASE", mode="optimistic", max_days=378, lo=lo * s, hi=hi * s) for i in st])
ok = [v for v in (0.08, 0.10, 0.12, 0.15, 0.20) if grid[f"{v}|SEL"]["P_fail_daily"] <= 0.05]
vs = max(ok, key=lambda v: grid[f"{v}|SEL"]["P_pass"]) if ok else None
out["prop_grid"] = grid; out["prop_chosen_vol"] = vs
F.append({"kind": "holdout_evaluation", "hypothesis_id": "GEN40_TF1_MT5", "protocol": PROTO,
          "result": {"TF1": {k_: g[k_] for k_ in ("DEV", "VAL", "TEST", "TEST_stress")}, "gates": out["gates_TF1"], "TF1_PASS": out["TF1_PASS"],
                     "COMBO_BETTER_CONSISTENCY": out["COMBO_BETTER_CONSISTENCY"]}})
(ROOT / "results/gen40_multiasset_trend.json").write_text(json.dumps(out, indent=1, default=float))
pd.to_pickle({"TF": TF * k, "COMBO": combo}, ROOT / "results/gen40_series.pkl")
print(json.dumps({k_: out[k_] for k_ in ("TF1", "TF1_BONDS_variant", "corr_TF1_Cstar", "gates_TF1", "TF1_PASS", "Cstar_alone_2018_2026",
                                          "TF1_alone_2018_2026", "COMBO_2018_2026", "COMBO_BETTER_CONSISTENCY", "prop_chosen_vol")}, indent=1, default=float))
for kk, v in grid.items():
    print(kk, v["P_pass"], v["P_fail_daily"], v["P_fail_max"], v["P_unresolved"], v["median_days_to_pass"])

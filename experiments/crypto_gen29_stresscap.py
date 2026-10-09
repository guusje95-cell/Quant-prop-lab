"""Gen29 (config/crypto_gen29_protocol.json): frozen E2 + STRESS_CAP overlay, CFT 2-Phase / 1-Phase with real daily lows."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.data import static_klines as SK  # noqa: E402
from qpl.prop_simulation import cft_daily as CFT  # noqa: E402
from qpl.research import factory as F  # noqa: E402
from qpl.strategies import cft_e2 as E  # noqa: E402

PROTO = "config/crypto_gen29_protocol.json"
COST = 7.5; SQ = np.sqrt(365); HORIZON = 548
SEL = ("2018-01-01", "2022-12-31"); TEST = ("2023-01-01", "2026-10-08"); FRESH = ("2026-05-24", "2026-10-08")
TEST_STARTS = ("2023-01-01", "2025-04-08")
GRID = {"2PHASE": (0.03, 0.04), "1PHASE": (0.025, 0.03)}
VOLS = (0.06, 0.08, 0.10, 0.12, 0.15, 0.20)

D = SK.load("1d")
c = D["close"].loc["2017-08-17":"2026-10-08"]; h, l = D["high"].reindex_like(c), D["low"].reindex_like(c)
ret = c.pct_change(fill_method=None)


def sh(x):
    x = x.dropna(); return float(x.mean() / x.std() * SQ) if len(x) > 30 and x.std() > 0 else 0.0


def engine(w, cmult=1.0, fund=0.0):
    wp = w.shift(1).fillna(0)
    cost = wp.diff().abs().sum(axis=1).fillna(0) * COST * cmult / 1e4
    gross = (wp * ret.fillna(0)).sum(axis=1)
    lo_r, hi_r = (l / c.shift(1) - 1).fillna(0), (h / c.shift(1) - 1).fillna(0)
    worst = (wp.clip(lower=0) * lo_r + wp.clip(upper=0) * hi_r).sum(axis=1) - cost
    best = (wp.clip(lower=0) * hi_r + wp.clip(upper=0) * lo_r).sum(axis=1) - cost
    f = (wp * fund * 3 / 1e4).sum(axis=1)
    return pd.DataFrame({"gross": gross, "net": gross - cost - f, "worst": worst, "best": best, "cost": cost,
                         "gross_exposure": wp.abs().sum(axis=1), "turnover": wp.diff().abs().sum(axis=1).fillna(0)}).loc["2018-01-01":]


def stats(d, a, z):
    x = d["net"].loc[a:z]; eq = (1 + x).cumprod()
    return {"net_sharpe": round(sh(x), 3), "gross_sharpe": round(sh(d["gross"].loc[a:z]), 3),
            "cagr": round(float(eq.iloc[-1] ** (365 / len(x)) - 1), 4), "ann_vol": round(float(x.std() * SQ), 4),
            "max_dd": round(float((eq / eq.cummax() - 1).min()), 4), "worst_intraday_day": round(float(d["worst"].loc[a:z].min()), 4),
            "pf_days": round(float(x[x > 0].sum() / -x[x < 0].sum()), 3), "avg_gross_exposure": round(float(d["gross_exposure"].loc[a:z].mean()), 3),
            "max_gross_exposure": round(float(d["gross_exposure"].loc[a:z].max()), 3), "turnover_per_yr": round(float(d["turnover"].loc[a:z].mean() * 365), 2)}


def prop(d, program, a, z, trunc=None):
    x, lo, hi = d["net"], d["worst"], d["best"]
    if trunc:
        x, lo, hi = x.loc[:trunc], lo.loc[:trunc], hi.loc[:trunc]
    idx = x.index; r = x.to_numpy()
    starts = [i for i in range(0, len(idx), 2) if pd.Timestamp(a) <= idx[i] <= pd.Timestamp(z)]
    return CFT.summarize([CFT.simulate_start(r, s, program, mode="optimistic", max_days=HORIZON, lo=lo.to_numpy(), hi=hi.to_numpy()) for s in starts])


w0 = E.raw_weights(c)
base = engine(w0)
L_unit = float(base["net"].loc[slice(*SEL)].std() * SQ)          # raw E2 vol 2018-2022 (identical to gen28 L_base)
out = {"raw_E2_check": stats(base, *SEL), "L_unit": L_unit, "grid": {}}
cache = {}
for prog, bs in GRID.items():
    for b in bs:
        for v in VOLS:
            key = (v, b)
            if key not in cache:
                cache[key] = engine(E.capped_weights(c, l, v / L_unit, b))
            d = cache[key]
            out["grid"][f"{prog}|v{v}|b{b}|SEL"] = prop(d, prog, *SEL, trunc=SEL[1])
            out["grid"][f"{prog}|v{v}|b{b}|TEST"] = prop(d, prog, *TEST_STARTS)
            out["grid"][f"{prog}|v{v}|b{b}|SEL"]["worst_day_all"] = round(float(d["worst"].min()), 4)
chosen = {}
for prog, bs in GRID.items():
    cand = [(v, b) for b in bs for v in VOLS if out["grid"][f"{prog}|v{v}|b{b}|SEL"]["P_fail_daily"] <= 0.05]
    chosen[prog] = max(cand, key=lambda k: out["grid"][f"{prog}|v{k[0]}|b{k[1]}|SEL"]["P_pass"]) if cand else None
out["chosen"] = {k: list(v) if v else None for k, v in chosen.items()}
res = {}
for prog, ch in chosen.items():
    if not ch:
        continue
    v, b = ch; d = cache[ch]; d2 = engine(E.capped_weights(c, l, v / L_unit, b), 2.0, 1.0)
    res[prog] = {"v": v, "b": b, "SEL": stats(d, *SEL), "TEST": stats(d, *TEST), "FRESH": stats(d, *FRESH),
                 "ALL_2018_2026": stats(d, "2018-01-01", "2026-10-08"), "TEST_stress": round(sh(d2["net"].loc[slice(*TEST)]), 3),
                 "by_year": {int(y): round(sh(g), 2) for y, g in d["net"].groupby(d["net"].index.year)},
                 "by_year_return": {int(y): round(float((1 + g).prod() - 1), 4) for y, g in d["net"].groupby(d["net"].index.year)},
                 "prop_SEL": out["grid"][f"{prog}|v{v}|b{b}|SEL"], "prop_TEST": out["grid"][f"{prog}|v{v}|b{b}|TEST"],
                 "worst_days": {str(k.date()): round(float(x), 4) for k, x in d["worst"].nsmallest(5).items()}}
    d.to_pickle(ROOT / f"results/crypto_gen29_{prog}_series.pkl")
out["chosen_results"] = res
r2 = res.get("2PHASE")
gates = {"G1": bool(r2 and r2["TEST"]["net_sharpe"] >= 0.8), "G2": bool(r2 and r2["TEST_stress"] >= 0.5),
         "G3": bool(r2 and r2["prop_TEST"]["P_pass"] >= 0.60 and r2["prop_TEST"]["P_fail_daily"] <= 0.05),
         "G4": bool(r2 and r2["ALL_2018_2026"]["worst_intraday_day"] > -0.05)}
out["gates"] = gates; out["APPLICABLE"] = all(gates.values())
F.append({"kind": "holdout_evaluation", "hypothesis_id": "GEN29_E2_STRESS_CAP", "protocol": PROTO,
          "result": {"chosen": out["chosen"], "gates": gates, "APPLICABLE": out["APPLICABLE"]}})
(ROOT / "results/crypto_gen29_stresscap.json").write_text(json.dumps(out, indent=1, default=float))
print("raw check", out["raw_E2_check"]["net_sharpe"], "L_unit", round(L_unit, 4))
for k, v in out["grid"].items():
    print(k, v["P_pass"], v["P_fail_daily"], v["P_fail_max"], v["P_unresolved"], v["median_days_to_pass"], v.get("worst_day_all", ""))
print(json.dumps(res, indent=1, default=float))
print("GATES", gates, "APPLICABLE", out["APPLICABLE"])

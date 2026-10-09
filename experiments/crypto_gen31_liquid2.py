"""Gen31 (config/crypto_gen31_protocol.json): E2 on BTC+ETH only (LIQUID2), gen30 EV-based risk selection."""
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

PROTO = "config/crypto_gen31_protocol.json"
COST = 7.5; SQ = np.sqrt(365); HORIZON = 548
SEL = ("2018-01-01", "2022-12-31"); TEST = ("2023-01-01", "2026-10-08"); FRESH = ("2026-05-24", "2026-10-08")
TEST_STARTS = ("2023-01-01", "2025-04-08")
GRID = {"2PHASE": (0.03, 0.04), "1PHASE": (0.025, 0.03)}
VOLS = (0.06, 0.08, 0.10, 0.12, 0.15, 0.20)

D = SK.load("1d")
c = D["close"].loc["2017-08-17":"2026-10-08", ["BTC", "ETH"]]; h, l = D["high"].reindex_like(c), D["low"].reindex_like(c)
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



SEL_STARTS = ("2018-01-01", "2020-12-31"); EV_STARTS = ("2023-01-01", "2024-06-30")
RISK = (0.04, 0.05, 0.06, 0.08, 0.10, 0.12)
FEE = {"2PHASE": 0.009, "1PHASE": 0.008}; FEE_STRESS = 0.015


def ev(p, fee):
    return round(0.95 * p["E_payout_frac_12m_per_attempt"] - fee, 4)


w0 = E.raw_weights(c)
L_unit = float(engine(w0)["net"].loc[slice(*SEL)].std() * SQ)
out = {"L_unit": L_unit, "grid": {}, "chosen": {}, "results": {}}
_d1 = engine(w0); _d2 = engine(w0, 2.0, 1.0)
out["strategy_unit"] = {"SEL": stats(_d1, *SEL), "TEST": stats(_d1, *TEST), "FRESH": stats(_d1, *FRESH), "TEST_stress": round(sh(_d2["net"].loc[slice(*TEST)]), 3),
                        "by_year": {int(y): round(sh(g), 2) for y, g in _d1["net"].groupby(_d1["net"].index.year)}}
G12 = out["strategy_unit"]["TEST"]["net_sharpe"] >= 0.8 and out["strategy_unit"]["TEST_stress"] >= 0.5
series = {v: engine(w0 * v / L_unit) for v in RISK}
for prog in FEE:
    for v in RISK:
        d = series[v]
        a = prop(d, prog, *SEL_STARTS, trunc=SEL[1]); b = prop(d, prog, *EV_STARTS)
        a["EV"] = ev(a, FEE[prog]); b["EV"] = ev(b, FEE[prog]); b["EV_fee_stress"] = ev(b, FEE_STRESS)
        out["grid"][f"{prog}|{v}|SEL"] = a; out["grid"][f"{prog}|{v}|TEST"] = b
    vstar = max(RISK, key=lambda v: out["grid"][f"{prog}|{v}|SEL"]["EV"])
    t = out["grid"][f"{prog}|{vstar}|TEST"]; d = series[vstar]
    out["chosen"][prog] = vstar
    out["results"][prog] = {"v": vstar, "L": round(vstar / L_unit, 4), "SEL_prop": out["grid"][f"{prog}|{vstar}|SEL"], "TEST_prop": t,
                            "strategy_ALL_2018_2026": stats(d, "2018-01-01", "2026-10-08"), "strategy_TEST": stats(d, *TEST), "strategy_FRESH": stats(d, *FRESH),
                            "by_year_return": {int(y): round(float((1 + g).prod() - 1), 4) for y, g in d["net"].groupby(d["net"].index.year)},
                            "worst_days": {str(k.date()): round(float(x), 4) for k, x in d["worst"].nsmallest(6).items()},
                            "gates": {"G1G2": bool(G12), "G3": bool(t["EV_fee_stress"] > 0 and t["P_pass"] >= 0.50), "G4": bool(t["P_fail_daily"] <= 0.10)},
                            "APPLICABLE": bool(G12 and t["EV_fee_stress"] > 0 and t["P_pass"] >= 0.50 and t["P_fail_daily"] <= 0.10)}
    d.to_pickle(ROOT / f"results/crypto_gen31_{prog}_series.pkl")
F.append({"kind": "holdout_evaluation", "hypothesis_id": "GEN31_E2_LIQUID2", "protocol": PROTO,
          "result": {p: {"v": r["v"], "TEST_P_pass": r["TEST_prop"]["P_pass"], "TEST_P_fail_daily": r["TEST_prop"]["P_fail_daily"],
                         "TEST_EV": r["TEST_prop"]["EV"], "APPLICABLE": r["APPLICABLE"]} for p, r in out["results"].items()}})
(ROOT / "results/crypto_gen31_ev.json").write_text(json.dumps(out, indent=1, default=float))
for k, v in out["grid"].items():
    print(k, "pass", v["P_pass"], "daily", v["P_fail_daily"], "max", v["P_fail_max"], "open", v["P_unresolved"], "med", v["median_days_to_pass"],
          "fsurv", v["funded_survive_12m"], "pay", v["E_payout_frac_12m_per_attempt"], "EV", v["EV"], v.get("EV_fee_stress", ""))
print(json.dumps(out["strategy_unit"], default=float))
print(json.dumps(out["results"], indent=1, default=float))

"""Gen28 (config/crypto_gen28_protocol.json): applicable CFT strategy on 10 Binance majors with real daily highs/lows.
Deviation (stricter): risk-selection simulations use returns truncated at 2022-12-31, so no 2023+ data leaks into v."""
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
from qpl.strategies import crypto_zoo as Z  # noqa: E402

PROTO = "config/crypto_gen28_protocol.json"
COST, FUND8H = 7.5, 1.0
SQ = np.sqrt(365)
SEL = ("2018-01-01", "2022-12-31"); TEST = ("2023-01-01", "2026-10-08"); FRESH = ("2026-05-24", "2026-10-08")
TEST_STARTS = ("2023-01-01", "2025-04-08")
VOLS = (0.06, 0.08, 0.10, 0.12, 0.15, 0.20)
HORIZON = 548

D = SK.load("1d")
o, h, l, c = D["open"], D["high"], D["low"], D["close"]
c = c.loc["2017-08-17":"2026-10-08"]; h, l = h.reindex_like(c), l.reindex_like(c)
ret = c.pct_change(fill_method=None)
hist = c.notna().cumsum() >= 200
sig30 = np.log(c).diff().rolling(30, min_periods=20).std() * SQ


def sh(x):
    x = x.dropna(); return float(x.mean() / x.std() * SQ) if len(x) > 30 and x.std() > 0 else 0.0


def ens(fns, mode):
    out = {}
    for a in c.columns:
        s = c[a].dropna()
        out[a] = Z.apply_mode(sum(fn(s) for fn in fns) / len(fns), mode)
    return pd.DataFrame(out).reindex_like(c).fillna(0)


BO = [lambda s, n=n, k=k: Z.short_breakout(s, n, k) for n in (5, 7, 10, 14, 20) for k in (1, 2, 3)]
TM = [lambda s, n=n: Z.tsmom(s, n) for n in (14, 30, 60, 90)]
E1 = ens(BO, "LO")
STRATS = {"E1_BREAKOUT_ENSEMBLE_LO": E1,
          "E2_TREND_BREAKOUT_LO": 0.5 * E1 + 0.5 * ens(TM, "LO"),
          "E3_TREND_BREAKOUT_LS": 0.5 * ens(BO, "LS") + 0.5 * ens(TM, "LS")}


def engine(sig, cmult=1.0, fund=0.0):
    n = hist.sum(axis=1).replace(0, np.nan)
    w = (sig * (0.40 / sig30).clip(upper=1.0)).where(hist, 0.0).div(n, axis=0).fillna(0)
    wp = w.shift(1).fillna(0)                                           # position held during day t (decided at close t-1)
    cost = w.shift(1).diff().abs().sum(axis=1).fillna(0) * COST * cmult / 1e4   # traded at the start of day t
    f = (wp * fund * 3 / 1e4).sum(axis=1)
    gross = (wp * ret.fillna(0)).sum(axis=1)
    lo_r, hi_r = l / c.shift(1) - 1, h / c.shift(1) - 1
    worst = (wp.clip(lower=0) * lo_r.fillna(0) + wp.clip(upper=0) * hi_r.fillna(0)).sum(axis=1) - cost
    best = (wp.clip(lower=0) * hi_r.fillna(0) + wp.clip(upper=0) * lo_r.fillna(0)).sum(axis=1) - cost
    return pd.DataFrame({"gross": gross, "net": gross - cost - f, "cost": cost, "worst": worst, "best": best,
                         "gross_exposure": wp.abs().sum(axis=1), "net_exposure": wp.sum(axis=1),
                         "turnover": w.diff().abs().sum(axis=1).fillna(0)}).loc["2018-01-01":]


def stats(d, a, z):
    x = d["net"].loc[a:z]; eq = (1 + x).cumprod()
    return {"net_sharpe": round(sh(x), 3), "gross_sharpe": round(sh(d["gross"].loc[a:z]), 3),
            "cagr": round(float(eq.iloc[-1] ** (365 / len(x)) - 1), 4), "ann_vol": round(float(x.std() * SQ), 4),
            "max_dd": round(float((eq / eq.cummax() - 1).min()), 4), "worst_intraday_day": round(float(d["worst"].loc[a:z].min()), 4),
            "hit_rate_days": round(float((x > 0).mean()), 3), "pf_days": round(float(x[x > 0].sum() / -x[x < 0].sum()), 3),
            "avg_gross_exposure": round(float(d["gross_exposure"].loc[a:z].mean()), 3), "turnover_per_yr": round(float(d["turnover"].loc[a:z].mean() * 365), 1)}


def prop(d, v, L_base, program, a, z, trunc=None):
    L = v / L_base
    x = d["net"] * L; lo = d["worst"] * L; hi = d["best"] * L
    if trunc:
        x, lo, hi = x.loc[:trunc], lo.loc[:trunc], hi.loc[:trunc]
    idx = x.index; r, lo_, hi_ = x.to_numpy(), lo.to_numpy(), hi.to_numpy()
    starts = [i for i in range(0, len(idx), 2) if pd.Timestamp(a) <= idx[i] <= pd.Timestamp(z)]
    return CFT.summarize([CFT.simulate_start(r, s, program, mode="optimistic", max_days=HORIZON, lo=lo_, hi=hi_) for s in starts])


out = {"n_trials_cumulative": 111, "strategies": {}}
for name, sig in STRATS.items():
    d1, d2 = engine(sig), engine(sig, 2.0, FUND8H)
    out["strategies"][name] = {"SEL_2018_2022": stats(d1, *SEL), "TEST_2023_2026": stats(d1, *TEST), "FRESH_2026_05_10": stats(d1, *FRESH),
                               "TEST_stress_2x_fund": round(sh(d2["net"].loc[slice(*TEST)]), 3),
                               "by_year": {int(y): round(sh(g), 2) for y, g in d1["net"].groupby(d1["net"].index.year)}}
    out["strategies"][name]["_d"] = d1
cand = max(STRATS, key=lambda k: out["strategies"][k]["SEL_2018_2022"]["net_sharpe"])
d = out["strategies"][cand]["_d"]
L_base = float(d["net"].loc[slice(*SEL)].std() * SQ)
grid = {}
for prog in ("2PHASE", "1PHASE"):
    for v in VOLS:
        grid[f"{prog}|{v}|SEL"] = prop(d, v, L_base, prog, *SEL, trunc=SEL[1])
        grid[f"{prog}|{v}|TEST"] = prop(d, v, L_base, prog, *TEST_STARTS)
chosen = {}
for prog in ("2PHASE", "1PHASE"):
    ok = [v for v in VOLS if grid[f"{prog}|{v}|SEL"]["P_fail_daily"] <= 0.05]
    chosen[prog] = max(ok, key=lambda v: grid[f"{prog}|{v}|SEL"]["P_pass"]) if ok else None
v2 = chosen["2PHASE"]
worst_at_v = float(d["worst"].min() * v2 / L_base) if v2 else None
gates = {"G1": out["strategies"][cand]["TEST_2023_2026"]["net_sharpe"] >= 0.8,
         "G2": out["strategies"][cand]["TEST_stress_2x_fund"] >= 0.5,
         "G3": bool(v2 and grid[f"2PHASE|{v2}|TEST"]["P_pass"] >= 0.60 and grid[f"2PHASE|{v2}|TEST"]["P_fail_daily"] <= 0.05),
         "G4": bool(v2 and worst_at_v > -0.05)}
out.update({"candidate": cand, "L_base_vol_2018_2022": round(L_base, 4), "chosen_vol": chosen, "worst_intraday_at_chosen_2phase": worst_at_v,
            "prop_grid": grid, "gates": gates, "APPLICABLE": all(gates.values())})
for k in STRATS:
    out["strategies"][k].pop("_d")
F.append({"kind": "holdout_evaluation", "hypothesis_id": f"GEN28_{cand}", "protocol": PROTO,
          "result": {"gates": gates, "chosen_vol": chosen, "APPLICABLE": out["APPLICABLE"]}})
(ROOT / "results/crypto_gen28_cft.json").write_text(json.dumps(out, indent=1, default=float))
d.to_pickle(ROOT / "results/crypto_gen28_series.pkl")
for k, v in out["strategies"].items():
    print(k, json.dumps(v))
print("CANDIDATE", cand, "L_base", L_base, "chosen", chosen, "worst@v", worst_at_v)
for k, v in grid.items():
    print(k, v["P_pass"], v["P_fail_daily"], v["P_fail_max"], v["P_unresolved"], v["median_days_to_pass"], v["funded_survive_12m"], v["E_payout_frac_12m_per_attempt"])
print("GATES", gates, "APPLICABLE", out["APPLICABLE"])

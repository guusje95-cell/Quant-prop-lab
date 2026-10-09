"""NOT RUN (stopped at user instruction 2026-10-10; FTMO is not a target unless requested).
Gen22 prop track: FTMO-universe trend (P22a) and trend+carry (P22b) with CFD costs + FTMO 2-Step simulation.
Protocol config/prop_ftmo_trend_protocol.json (committed dbe5393 before any return on this universe)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import panel as PB  # noqa: E402
from qpl.data import futures_panel as FP  # noqa: E402
from qpl.prop_simulation import ftmo_daily as FD  # noqa: E402
from qpl.research import factory as F, v6  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import f9, futures_factors as FF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/prop_ftmo_trend_protocol.json"
PR = json.loads((ROOT / PROTO).read_text())
PER = PR["periods"]
P = FP.build(); U, _ = FP.universe(P)
umap = PR["universe_map (FTMO CFD -> pysystemtrade proxy; list UNCERTAIN)"]
names = [n for k in ("indices", "fx", "metals", "energy", "ags") for n in umap[k]]
use = [n for n in names if n in U]
missing = [n for n in names if n not in U]
ret, cost, cy = P["ret"][use], P["cost"][use], P["carry"][use]
SIG = PB.sigma(ret)


def cap(W, L=8.0):
    lev = W.abs().sum(axis=1)
    return W.mul((L / lev).clip(upper=1.0).fillna(1.0), axis=0)


def book(kind):
    if kind == "P22a_TREND":
        s = ((FF.ct1_transfer(ret).fillna(0) + FF.tsmom(ret).fillna(0) + FF.ewmac(ret).fillna(0)) / 3).where(ret.notna().cumsum() > 0)
        _, W = PB.run(ret, s, cost, sig=SIG, return_weights=True)
        W = f9.buffer_weights(W, 0.05)
    else:
        W = f9.weights(ret, cost, cy)
    return cap(W)


def pnl(W, spread_mult, markup):
    d = f9.pnl(ret, cost, W, cost_mult=spread_mult)
    fin = W.shift(2).abs().sum(axis=1) * markup / 256.0
    d["financing"] = fin
    d["net"] = d["net"] - fin
    d = d.resample("B").sum()                                        # business-day series (weekend/holiday rows folded in)
    return d


def conv(d, a, z):
    x = d.loc[a:z]
    st = PB.stats(x["net"]); g = PB.stats(x["gross"])["sharpe"]
    lo, hi, _ = T.bootstrap_ci(x["net"].to_numpy(), T.sharpe, n_boot=1000, block=20)
    eq = (1 + x["net"]).cumprod()
    yrs = len(x) / 260
    cagr = float(eq.iloc[-1] ** (1 / yrs) - 1)
    mdd = float((eq / eq.cummax() - 1).min())
    return {"net_sharpe": round(st["sharpe"], 3), "gross_sharpe": round(g, 3), "sharpe_ci95": [round(lo * np.sqrt(256 / 252), 2), round(hi * np.sqrt(256 / 252), 2)],
            "cagr": round(cagr, 4), "ann_vol": round(st["ann_vol"], 4), "max_dd": round(mdd, 4), "calmar": round(cagr / abs(mdd), 2) if mdd < 0 else None,
            "costs_pa": round(float(x["cost"].mean() * 260), 4), "financing_pa": round(float(x["financing"].mean() * 260), 4),
            "turnover_pa": round(float(x["turnover"].mean() * 260), 1), "mean_gross_notional": round(float(x["gross_lev"].mean() / 1), 2),
            "share_pos_months": round(float((x["net"].resample("ME").sum() > 0).mean()), 3)}


def prop_block(d, v, mode, a, z):
    r = (d["net"] * v / 0.10).to_numpy()
    idx = d.index
    starts = [i for i in range(0, len(idx), 10) if a <= idx[i] <= pd.Timestamp(z)]
    return FD.summarize([FD.simulate_start(r, s, mode=mode) for s in starts])


def bootstrap(d, v, mode, n=3000, horizon=1100, seed=3):
    x = (d["net"].loc["2010":"2024"] * v / 0.10).to_numpy()
    idx = T.stationary_bootstrap_indices(len(x), n, 20, np.random.default_rng(seed))
    res = []
    for row in idx:
        path = np.resize(x[row], horizon) if len(row) < horizon else x[row][:horizon]
        res.append(FD.simulate_start(path, 0, mode=mode))
    return FD.summarize(res)


out = {"universe_used": use, "missing_from_universe": missing, "n_instruments": len(use)}
for kind in ("P22a_TREND", "P22b_TREND_CARRY"):
    F.Hypothesis(kind, "prop/ftmo-trend", PR["strategies"][kind], "time-series momentum / carry premia on FTMO-tradable CFD underlyings",
                 json.dumps(PR["gates"]), "pysystemtrade proxy", "vol target grid", "none", PROTO, generation=22).register()
    W = book(kind)
    base, stress = pnl(W, 2.0, 0.025), pnl(W, 4.0, 0.05)
    res = {"conventional": {p: conv(base, *PER[p]) for p in PER}, "stress": {p: conv(stress, *PER[p])["net_sharpe"] for p in PER}}
    res["by_year_net"] = {int(y): round(float(v), 4) for y, v in base["net"].groupby(base.index.year).sum().loc[1990:].items()}
    cv, cd = res["conventional"]["VALIDATION"], res["conventional"]["DISCOVERY"]
    res["conv_pass"] = bool(cv["net_sharpe"] >= 0.4 and cd["net_sharpe"] >= 0.6 and res["stress"]["VALIDATION"] > 0)
    grid = {}
    for v in (0.06, 0.08, 0.10, 0.12, 0.15):
        grid[v] = {m: prop_block(base, v, m, pd.Timestamp("1990-01-01"), "2013-12-31") for m in ("optimistic", "conservative")}
    ok = {v: g["conservative"] for v, g in grid.items() if g["conservative"]["P_fail_eval"] <= 0.35}
    vstar = max(ok, key=lambda v: ok[v]["P_pass_both_within_24m"]) if ok else None
    res["prop_grid_1990_2013"] = {str(v): g for v, g in grid.items()}
    res["chosen_vol"] = vstar
    if vstar:
        res["prop_chosen_pre2014"] = grid[vstar]
        res["prop_chosen_post2014_contaminated"] = {m: prop_block(base, vstar, m, pd.Timestamp("2014-01-01"), "2024-03-28") for m in ("optimistic", "conservative")}
        res["prop_chosen_bootstrap_2010_2024"] = {m: bootstrap(base, vstar, m) for m in ("optimistic", "conservative")}
        res["prop_chosen_stress_costs_pre2014"] = prop_block(stress, vstar, "conservative", pd.Timestamp("1990-01-01"), "2013-12-31")
        g = grid[vstar]["conservative"]
        res["prop_pass"] = bool(g["P_pass_both_within_24m"] >= 0.5 and g["P_fail_eval"] <= 0.35)
    else:
        res["prop_pass"] = False
    verdict = "REJECTED" if not res["conv_pass"] else ("PROMISING_BUT_UNVALIDATED" if res["prop_pass"] else "EXPLORATORY")
    res["verdict"] = verdict
    v6.record(kind, "prop/ftmo-trend", kind, {"vol": vstar}, "DISC/VAL+prop", {"conv": res["conventional"], "stress": res["stress"], "vstar": vstar}, 22, PROTO, "FTMO universe")
    F.decide(F.Hypothesis(kind, "", "", "", "", "", "", "", PROTO, generation=22), verdict,
             json.dumps({"VAL": cv["net_sharpe"], "DISC": cd["net_sharpe"], "vstar": vstar, "prop": res.get("prop_chosen_pre2014", {}).get("conservative")})[:600], {"protocol": PROTO})
    out[kind] = res
    base.to_parquet(ROOT / f"results/prop_ftmo_gen22_{kind}_pnl.parquet")
    print(kind, json.dumps({"conv": res["conventional"], "stress": res["stress"], "vstar": vstar, "verdict": verdict}, default=str), flush=True)
(ROOT / "results/prop_ftmo_gen22.json").write_text(json.dumps(out, indent=1, default=str))

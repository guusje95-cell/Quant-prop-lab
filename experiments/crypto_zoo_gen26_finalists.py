"""Gen26 stage 3: finalists that passed DEV + VAL with TEST net >= 0.6. Remaining pre-registered gates:
TEST at 2x costs >= 0.4, DSR (N = 104 configs) >= 0.90 on DEV+VAL, PBO reported, CFT 2-Phase pass >= 60% with daily-loss
breaches <= 10% at a risk level chosen on DEV+VAL only. Plus descriptive robustness (neighbours, coins, years, 3x costs)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("zoo", ROOT / "experiments/crypto_zoo_gen26.py")
src = (ROOT / "experiments/crypto_zoo_gen26.py").read_text().split("# ------------------------------------------------------------------ configs")[0]
G: dict = {"__name__": "zoo_head", "__file__": str(Path(__file__).resolve().parent / "crypto_zoo_gen26.py")}
exec(compile(src, "zoo_head", "exec"), G)                        # engines + data (no records written)
from qpl.prop_simulation import cft_daily as CFT  # noqa: E402
from qpl.research import factory as F  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import crypto_zoo as Z  # noqa: E402

btc, px, PER, sh = G["btc"], G["px"], G["PER"], G["sh"]
FIN = {
    "MULTI_SHORT_BREAKOUT_7_2_LO": ("MULTI", lambda c: Z.short_breakout(c, 7, 2), "LO"),
    "MULTI_RSI_MOMENTUM_14_LO": ("MULTI", lambda c: Z.rsi_momentum(c, 14, 55, 45), "LO"),
    "BTC_TSMOM_30_LS": ("BTC", lambda c: Z.tsmom(c, 30), "LS"),
    "BTC_TSMOM_30_LO": ("BTC", lambda c: Z.tsmom(c, 30), "LO"),
}
NEIGH = {
    "MULTI_SHORT_BREAKOUT_7_2_LO": [(n, h) for n in (5, 7, 10, 14) for h in (1, 2, 3, 5)],
    "MULTI_RSI_MOMENTUM_14_LO": [(n, u) for n in (7, 14, 21) for u in (52, 55, 60)],
    "BTC_TSMOM_30_LS": [20, 25, 30, 40, 50, 60], "BTC_TSMOM_30_LO": [20, 25, 30, 40, 50, 60],
}


def run(ds, fn, mode, cm=1.0, fm=1.0):
    if ds == "BTC":
        return G["btc_daily"](Z.apply_mode(fn(btc.close), mode), cm, fm)
    sig = pd.DataFrame({a: Z.apply_mode(fn(px[a].dropna()), mode) for a in px.columns if px[a].notna().sum() > 250})
    return G["multi_daily"](sig, cm, fm)


def period_stats(d, bh, a, z):
    x = d["net"].loc[a:z]; y = bh.loc[a:z]
    beta = np.cov(x, y)[0, 1] / y.var()
    eq = (1 + x).cumprod(); yrs = len(x) / 365
    cagr = float(eq.iloc[-1] ** (1 / yrs) - 1); mdd = float((eq / eq.cummax() - 1).min())
    lo, hi, _ = T.bootstrap_ci(x.to_numpy(), T.sharpe, n_boot=1000, block=20)
    return {"net_sharpe": round(sh(x), 3), "gross_sharpe": round(sh(d["gross"].loc[a:z]), 3), "sharpe_ci95": [round(lo * np.sqrt(365 / 252), 2), round(hi * np.sqrt(365 / 252), 2)],
            "resid_sharpe": round(sh(x - beta * y), 3), "beta_to_bh": round(float(beta), 3), "cagr": round(cagr, 4), "ann_vol": round(float(x.std() * np.sqrt(365)), 4),
            "max_dd": round(mdd, 4), "calmar": round(cagr / abs(mdd), 2) if mdd < 0 else None, "cost_pa": round(float(d["cost"].loc[a:z].mean() * 365), 4),
            "funding_pa": round(float(d.get("funding", pd.Series(0, index=d.index)).loc[a:z].mean() * 365), 4), "turnover_pa": round(float(d["turnover"].loc[a:z].mean() * 365), 1),
            "days": int(len(x))}


def trade_stats(ds, fn, mode, a, z):
    """Episodes of non-zero position per asset; P&L = sum of w*r over the episode minus turnover costs (per asset)."""
    if ds == "BTC":
        s = Z.apply_mode(fn(btc.close), mode); closes = {"BTC": btc.close}; sigs = {"BTC": s}
        r = {"BTC": btc.close.pct_change()}
    else:
        closes = {a_: px[a_].dropna() for a_ in px.columns if px[a_].notna().sum() > 250}
        sigs = {a_: Z.apply_mode(fn(c), mode) for a_, c in closes.items()}
        r = {a_: c.pct_change() for a_, c in closes.items()}
    pnl = []
    for k, s in sigs.items():
        c = closes[k]; v = np.log(c).diff().rolling(30, min_periods=20).std() * np.sqrt(365)
        w = (s * 0.4 / v).clip(-1, 1).fillna(0)
        if ds == "MULTI":
            w = w.where(G["member"][k].reindex(w.index).fillna(False), 0.0)
        p = (w.shift(1) * r[k]).fillna(0) - w.diff().abs().fillna(0) * 7.5e-4
        ep = (np.sign(w) != np.sign(w.shift(1))).cumsum()
        df = pd.DataFrame({"p": p, "ep": ep, "on": w.shift(1).fillna(0) != 0}).loc[a:z]
        tr = df[df.on].groupby("ep").p.sum()
        pnl += list(tr.values)
    t = np.array(pnl)
    if len(t) == 0:
        return {}
    return {"trades": int(len(t)), "win_rate": round(float((t > 0).mean()), 3), "profit_factor": round(float(t[t > 0].sum() / -t[t < 0].sum()), 3),
            "avg_trade_pct_of_asset_book": round(float(t.mean() * 100), 3), "avg_win": round(float(t[t > 0].mean() * 100), 3), "avg_loss": round(float(t[t < 0].mean() * 100), 3)}


# selection-bias inputs: all 104 configs' daily series on DEV+VAL
series = pd.read_pickle(ROOT / "results/crypto_zoo_gen26_series.pkl")
mats = {}
for ds in ("BTC", "MULTI"):
    a, z = PER[ds]["DEV"][0], PER[ds]["VAL"][1]
    mats[ds] = pd.DataFrame({k: v["net"].loc[a:z] for k, v in series.items() if k[0] == ds}).fillna(0)
allsr = pd.concat([m.mean() / m.std() for m in mats.values()])
var_sr = float(allsr.var()); N = len(series)
pbo_src = (ROOT / "experiments/v3_pbo.py").read_text().split("def daily_matrix")[0]
PB: dict = {"__name__": "pbo", "__file__": str(ROOT / "experiments/v3_pbo.py")}
exec(compile(pbo_src, "pbo", "exec"), PB)
out = {"n_configs": N, "PBO": {ds: PB["cscv_pbo"](m.to_numpy(), S=16) for ds, m in mats.items()}}
for name, (ds, fn, mode) in FIN.items():
    bh = G["BTC_BH"] if ds == "BTC" else G["MULTI_BH"]
    d1, d2, d3 = run(ds, fn, mode), run(ds, fn, mode, 2.0, 2.0), run(ds, fn, mode, 3.0, 2.0)
    res = {"periods": {p: period_stats(d1, bh, *PER[ds][p]) for p in PER[ds]},
           "TEST_2x": round(sh(d2["net"].loc[slice(*PER[ds]["TEST"])]), 3), "TEST_3x": round(sh(d3["net"].loc[slice(*PER[ds]["TEST"])]), 3),
           "trades": {p: trade_stats(ds, fn, mode, *PER[ds][p]) for p in ("DEV", "VAL", "TEST")}}
    dv = d1["net"].loc[PER[ds]["DEV"][0]:PER[ds]["VAL"][1]].to_numpy()
    res["DSR_devval"] = round(T.deflated_sharpe(dv, N, var_sr), 4)
    res["by_year_net_sharpe"] = {int(y): round(sh(g), 2) for y, g in d1["net"].loc["2015":].groupby(d1["net"].loc["2015":].index.year) if len(g) > 60}
    # neighbours (descriptive robustness)
    nb = {}
    for p in NEIGH[name]:
        if name.startswith("MULTI_SHORT"):
            f = lambda c, n=p[0], h=p[1]: Z.short_breakout(c, n, h)
        elif name.startswith("MULTI_RSI"):
            f = lambda c, n=p[0], u=p[1]: Z.rsi_momentum(c, n, u, 100 - u)
        else:
            f = lambda c, n=p: Z.tsmom(c, n)
        dn = run(ds, f, mode)
        nb[str(p)] = {k_: round(sh(dn["net"].loc[slice(*PER[ds][k_])]), 2) for k_ in ("DEV", "VAL", "TEST")}
    res["neighbours"] = nb
    if ds == "MULTI":                                         # per-coin contribution in TEST (leave-one-out)
        sig = pd.DataFrame({a_: Z.apply_mode(fn(px[a_].dropna()), mode) for a_ in px.columns if px[a_].notna().sum() > 250})
        a, z = PER[ds]["TEST"]
        held = (sig.reindex_like(px).fillna(0).where(G["member"], 0) != 0).loc[a:z].mean()
        res["test_coins_held_share"] = held[held > 0].round(3).sort_values(ascending=False).head(15).to_dict()
        loo = {}
        for coin in held[held > 0.05].index:
            loo[coin] = round(sh(G["multi_daily"](sig.drop(columns=coin))["net"].loc[a:z]), 2)
        res["test_leave_one_coin_out"] = loo
    # gates
    res["gate_test"] = bool(res["periods"]["TEST"]["net_sharpe"] >= 0.6 and res["TEST_2x"] >= 0.4)
    res["gate_dsr"] = bool(res["DSR_devval"] >= 0.90)
    # CFT prop: choose vol on DEV+VAL starts only, then report TEST starts
    x = d1["net"]; vol_now = x.loc[PER[ds]["DEV"][0]:PER[ds]["VAL"][1]].std() * np.sqrt(365)
    grid = {}
    for v in (0.10, 0.15, 0.20, 0.25, 0.30):
        r = (x * v / vol_now).to_numpy(); idx = x.index
        for prog in ("2PHASE", "1PHASE"):
            for mode_ in ("optimistic", "conservative"):
                for per_ in ("DEVVAL", "TEST"):
                    a, z = (PER[ds]["DEV"][0], PER[ds]["VAL"][1]) if per_ == "DEVVAL" else PER[ds]["TEST"]
                    starts = [i for i in range(0, len(idx), 3) if pd.Timestamp(a) <= idx[i] <= pd.Timestamp(z)]
                    grid[f"{v}|{prog}|{mode_}|{per_}"] = CFT.summarize([CFT.simulate_start(r, s, prog, mode=mode_) for s in starts])
    res["cft_grid"] = grid
    ok = [v for v in (0.10, 0.15, 0.20, 0.25, 0.30) if grid[f"{v}|2PHASE|conservative|DEVVAL"]["P_fail_daily"] <= 0.10]
    vstar = max(ok, key=lambda v: grid[f"{v}|2PHASE|conservative|DEVVAL"]["P_pass"]) if ok else None
    res["chosen_vol"] = vstar
    if vstar:
        res["gate_prop"] = bool(grid[f"{vstar}|2PHASE|conservative|DEVVAL"]["P_pass"] >= 0.60)
        res["prop_chosen"] = {k: v for k, v in grid.items() if k.startswith(f"{vstar}|")}
    else:
        res["gate_prop"] = False
    res["ALL_GATES"] = bool(res["gate_test"] and res["gate_dsr"] and res["gate_prop"])
    out[name] = res
    F.append({"kind": "holdout_evaluation", "hypothesis_id": f"ZOO_{name}", "protocol": "config/crypto_zoo_protocol.json",
              "result": {"TEST": res["periods"]["TEST"]["net_sharpe"], "TEST_2x": res["TEST_2x"], "DSR": res["DSR_devval"], "chosen_vol": vstar,
                         "gates": {k: res[k] for k in ("gate_test", "gate_dsr", "gate_prop", "ALL_GATES")}}})
    print(name, json.dumps({k: res[k] for k in ("TEST_2x", "TEST_3x", "DSR_devval", "chosen_vol", "gate_test", "gate_dsr", "gate_prop", "ALL_GATES")}), flush=True)
(ROOT / "results/crypto_zoo_gen26_finalists.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out["PBO"], indent=1))

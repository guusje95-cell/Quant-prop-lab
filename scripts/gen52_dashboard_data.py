"""Builds results/dashboard/gen52_dashboard.json: equity curves, drawdowns, monthly returns, stats and prop cash curves."""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen52_optimize as G
from qpl.lab import propfirms as PF, strategies as S, analysis as A
import gen52_extra_check as X  # noqa: F401  (runs its own prints; reuse hourly())

CR = G.CR
sig = {"C* (plain)": (S.CStarTrend().signal(CR, S.CStarTrend().defaults()), 30, 0.0),
       "C* vol20 band0.2": (S.CStarTrend().signal(CR, S.CStarTrend().defaults()), 20, 0.2),
       "C* no filter vol20 band0.2 (FTMO pick)": (S.CStarTrend().signal(CR, {"stablecoin_filter": False, "long_only": True}), 20, 0.2),
       "Catching Crypto Trends": (S.CryptoTrendEnsemble().signal(CR, S.CryptoTrendEnsemble().defaults()), 30, 0.0),
       "Time-series momentum 60": (S.TSMOM().signal(CR, {"lookback": 60, "long_only": True}), 30, 0.0),
       "Donchian 55": (S.Donchian().signal(CR, {"n": 55, "long_only": True}), 30, 0.0)}
sig["C* + CCT 50/50"] = ((sig["C* (plain)"][0] + sig["Catching Crypto Trends"][0]) / 2, 30, 0.0)
sig = {"C* + BTC leads (Gen53)": (S.CStarTrend().signal(CR, {**S.CStarTrend().defaults(), "btc_leads": True}), 30, 0.0), **sig}
out = {"series": {}, "stats": {}, "monthly": {}, "drawdown": {}}
W = {}
for nm, (sg, look, b) in sig.items():
    w, d = G.backtest(sg, look, b); W[nm] = w
    x = d["net"]; eq = (1 + x).cumprod(); dd = eq / eq.cummax() - 1
    wk = eq.resample("W").last(); out["series"][nm] = [[t.strftime("%Y-%m-%d"), round(float(v), 4)] for t, v in wk.items()]
    out["drawdown"][nm] = [[t.strftime("%Y-%m-%d"), round(float(v), 4)] for t, v in dd.resample("W").min().items()]
    Sm = A.summary(x, 365); m = (1 + x).resample("ME").prod() - 1
    dev, tst = x.loc[G.DEV[0]:G.DEV[1]], x.loc[G.TEST[0]:]
    out["stats"][nm] = {"sharpe": Sm["Sharpe"], "cagr": Sm["CAGR"], "vol": Sm["Volatility"], "maxdd": Sm["Max drawdown"], "calmar": Sm["Calmar"],
                        "pos_months": Sm["Positive months"], "worst_month": Sm["Worst month"], "best_month": Sm["Best month"],
                        "sharpe_dev": float(dev.mean() / dev.std() * np.sqrt(365)), "sharpe_test": float(tst.mean() / tst.std() * np.sqrt(365))}
    out["monthly"][nm] = {t.strftime("%Y-%m"): round(float(v), 4) for t, v in m.items()}
btc = CR.close["BTC"].loc[G.DEV[0]:].dropna(); r = btc.pct_change().fillna(0) * (0.15 / (btc.pct_change().loc[G.DEV[0]:G.DEV[1]].std() * np.sqrt(365)))
eq = (1 + r).cumprod(); out["series"]["BTC buy & hold (15% vol)"] = [[t.strftime("%Y-%m-%d"), round(float(v), 4)] for t, v in eq.resample("W").last().items()]
out["drawdown"]["BTC buy & hold (15% vol)"] = [[t.strftime("%Y-%m-%d"), round(float(v), 4)] for t, v in (eq / eq.cummax() - 1).resample("W").min().items()]
Sm = A.summary(r, 365); out["stats"]["BTC buy & hold (15% vol)"] = {"sharpe": Sm["Sharpe"], "cagr": Sm["CAGR"], "vol": Sm["Volatility"], "maxdd": Sm["Max drawdown"],
    "calmar": Sm["Calmar"], "pos_months": Sm["Positive months"], "worst_month": Sm["Worst month"], "best_month": Sm["Best month"],
    "sharpe_dev": float(r.loc[G.DEV[0]:G.DEV[1]].mean() / r.loc[G.DEV[0]:G.DEV[1]].std() * np.sqrt(365)), "sharpe_test": float(r.loc[G.TEST[0]:].mean() / r.loc[G.TEST[0]:].std() * np.sqrt(365))}
# prop cash curves on the hourly path
out["prop"] = {}
for tag, nm, fn, sc, sf, stop, tp in (("Crypto Fund Trader 1-Phase: C* + BTC leads", "C* + BTC leads (Gen53)", "CFT1", 1.0, 0.4, 0, 0),
                                       ("FTMO 2-Step: C* + BTC leads", "C* + BTC leads (Gen53)", "FTMO", 1.0, 0.4, 0, 0),
                                       ("Crypto Fund Trader 1-Phase: plain C*", "C* (plain)", "CFT1", 1.0, 0.4, 0, 0),
                                       ("FTMO 2-Step: plain C*", "C* (plain)", "FTMO", 1.0, 0.4, 0, 0),
                                       ("FTMO 2-Step: optimised", "C* no filter vol20 band0.2 (FTMO pick)", "FTMO", 1.5, 0.6, 0.9, 0.04)):
    f0 = G.FIRMS[fn]
    hc = X.hourly(W[nm], sc, stop, tp, f0.daily_loss); hf = X.hourly(W[nm], sf, stop, tp, f0.daily_loss)
    a = PF.attempts(hc, f0, 1.0); p = PF.pipeline(hc, f0, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5)
    cv = p["curve"].iloc[::7]
    out["prop"][tag] = {"pass": a["P_pass"], "fail_daily": a["P_fail_daily"], "fail_max": a["P_fail_max"], "funded": p["P_funded"],
                        "net": p["net_mean"], "p10": p["net_p10"], "p50": p["net_p50"], "p90": p["net_p90"], "p_profit": p["P_profit"],
                        "bought": p["bought"], "fees": p["fees"], "paid": p["paid"], "paths": p["n"],
                        "curve": {k: [round(float(v)) for v in cv[k]] for k in ("p10", "p50", "p90", "mean")}, "week": list(range(len(cv)))}
s2 = pd.read_csv(ROOT / "results/gen52_stage2.csv")
out["sensitivity"] = {fn: {col: {str(k): round(float(v)) for k, v in s2[s2.firm == fn].groupby(col)["net"].mean().items()}
                           for col in ("risk_challenge", "risk_funded", "daily_stop", "take_profit", "cushion")} for fn in ("CFT1", "FTMO")}
out["final"] = pd.read_csv(ROOT / "results/gen52_final.csv")[["firm", "baseline", "config", "risk_challenge", "risk_funded", "daily_stop", "take_profit",
                                                              "cushion", "DEV_net", "TEST_pass", "TEST_net", "TEST_p_profit", "HOURLY_pass", "HOURLY_net",
                                                              "HOURLY_p_profit"]].round(4).to_dict("records")
def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list): return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)): return None if not np.isfinite(o) else round(float(o), 4)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    return o
g = pd.concat([pd.read_csv(ROOT / "results/gen53_research.csv"), pd.read_csv(ROOT / "results/gen53_btc_leads_pit.csv")])
g = g.drop_duplicates("test", keep="last")
def verdict(t):
    if t.startswith("H1") or t.startswith("PIT top") and "BTC" not in t: return "Info: bias check"
    if "base" in t or t.startswith("H2 single"): return "Baseline"
    if "BTC leads" in t: return "Pass"
    if t.startswith("H2 four"): return "Not passed (+0.07)"
    return "Rejected"
g["verdict"] = g["test"].map(verdict)
out["gen53"] = g[["test", "sharpe", "sharpe_dev", "sharpe_test", "cagr", "max_dd", "worst_day", "verdict"]].to_dict("records")
f55 = pd.read_csv(ROOT / "results/gen55_firms.csv")
out["gen55"] = f55[["firm", "setting", "risk_challenge", "risk_funded", "daily_stop", "pass", "funded", "fees", "net", "net_p50", "net_p10",
                    "p_profit", "months_with_income", "fee", "cost_bps", "swap_bps_day"]].sort_values("net", ascending=False).to_dict("records")
(ROOT / "results/dashboard").mkdir(parents=True, exist_ok=True)
json.dump(clean(out), open(ROOT / "results/dashboard/gen52_dashboard.json", "w"))
tpl = (ROOT / "results/dashboard/template.html").read_text()
(ROOT / "results/dashboard/prop_strategy_results.html").write_text(tpl.replace("__DATA__", json.dumps(clean(out))))
print("ok", {k: round(v["sharpe"], 2) for k, v in out["stats"].items()})
print({k: (round(v["net"]), round(v["pass"], 2)) for k, v in out["prop"].items()})

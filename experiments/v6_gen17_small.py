"""V6 gen17: small-account F9 (protocol config/v6_gen17_small_protocol.json)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import panel as PB
from qpl.data import futures_panel as FP
from qpl.research import factory as F, v6
from qpl.strategies import f9
ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/v6_gen17_small_protocol.json"
P = FP.build(); cfg = FP.meta(); q = FP.quality(P)
CLASSES = ["Equity", "Bond", "FX", "Ags", "Metals", "OilGas"]
kept, dropped = FP.dedupe(P)
groups = {k: [k] + [d for d, kk in dropped.items() if kk == k] for k in kept}
allm = [m for g in groups.values() for m in g if m in cfg.index]
N = FP.contract_notional(P, allm)
pool = {}
for k, g in groups.items():
    g = [m for m in g if m in cfg.index and cfg.loc[m, "AssetClass"] in CLASSES and not m.upper().startswith(("BITCOIN", "ETHER"))
         and q.loc[m, "ann_vol"] < 1.5 and q.loc[m, "longest_zero_return_run"] <= 60 and q.loc[m, "median_cost_bp"] / 1e4 / q.loc[m, "ann_vol"] <= 0.015]
    if not g:
        continue
    risk = {m: float((N[m] * P["ret"][m].rolling(256, min_periods=128).std() * 16).loc["2015":"2023"].median()) for m in g}
    risk = {m: v for m, v in risk.items() if np.isfinite(v)}
    if risk:
        m = min(risk, key=risk.get); pool[m] = (cfg.loc[m, "AssetClass"], risk[m])
out = {}
for C in (100_000, 250_000):
    best = None
    for K in range(30, 2, -1):
        aff = {m: v for m, v in pool.items() if v[1] <= C * 0.05 / K}
        bycls = {c: sorted([m for m, v in aff.items() if v[0] == c], key=lambda m: aff[m][1]) for c in CLASSES}
        pick, i = [], 0
        while len(pick) < K and any(len(v) > i for v in bycls.values()):
            for c in CLASSES:
                if len(bycls[c]) > i and len(pick) < K:
                    pick.append(bycls[c][i])
            i += 1
        if len(pick) == K:
            best = (K, pick); break
    if best is None:
        out[C] = {"K": 0, "verdict": "REJECTED", "why": "no affordable diversified set"}; continue
    K, pick = best
    ret, cost, cy = P["ret"][pick], P["cost"][pick], P["carry"][pick]
    W = f9.weights(ret, cost, cy)
    cont = f9.pnl(ret, cost, W)["net"]
    notional = N[pick]
    tgt = (W * C / notional).replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()
    held = np.zeros(K); H = np.zeros_like(tgt)
    for t in range(len(tgt)):
        trade = np.abs(tgt[t] - held) > 0.5 + 0.1 * np.abs(tgt[t])
        held = np.where(trade, np.round(tgt[t]), held); H[t] = held
    Wr = pd.DataFrame(H, index=W.index, columns=pick) * notional.fillna(0.0) / C
    integ = f9.pnl(ret, cost, Wr)["net"]
    def s(x, a, z):
        st = PB.stats(x.loc[a:z]); return {"sharpe": round(st["sharpe"], 3), "vol": round(st["ann_vol"], 3), "max_dd": round(st["max_dd"], 3)}
    res = {"K": K, "instruments": {m: pool[m][0] for m in pick},
           "integer": {"DISC_1990_2004": s(integ, "1990", "2004"), "VALIDATION": s(integ, "2005", "2013"), "2014_2024_contaminated": s(integ, "2014", "2024")},
           "continuous": {"DISC_1990_2004": s(cont, "1990", "2004"), "VALIDATION": s(cont, "2005", "2013"), "2014_2024_contaminated": s(cont, "2014", "2024")},
           "n_present_2005": int(ret.loc["2005"].notna().any().sum())}
    iv, idc = res["integer"]["VALIDATION"], res["integer"]["DISC_1990_2004"]
    res["verdict"] = "PROMISING_BUT_UNVALIDATED" if iv["sharpe"] >= 0.4 and iv["vol"] >= 0.06 and idc["sharpe"] >= 0.4 else "REJECTED"
    out[C] = res
    hid = f"G17_SMALL_{C // 1000}K"
    F.Hypothesis(hid, "futures/small-account implementation", f"F9 on {K} affordable instruments at ${C:,}", "diversified trend+carry with contract granularity",
                 json.load(open(ROOT / PROTO))["gate"], "pysystemtrade", "rule-based selection", "continuous F9", PROTO, generation=17).register()
    v6.record(hid, "futures/small-account implementation", "F9_small", {"capital": C}, "DISC/VAL", res, 17, PROTO, "futures panel")
    F.decide(F.Hypothesis(hid, "", "", "", "", "", "", "", PROTO, generation=17), res["verdict"], json.dumps({k: res[k] for k in ("K", "integer")})[:450], {"protocol": PROTO})
    print(C, json.dumps(res, indent=1))
(ROOT / "results/v6_gen17_small.json").write_text(json.dumps(out, indent=1, default=float))

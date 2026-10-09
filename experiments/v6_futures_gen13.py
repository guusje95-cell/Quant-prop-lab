"""V6 generation 13: futures factor families on the pysystemtrade panel. Protocol: config/v6_futures_protocol.json
(committed bb24d93 before any strategy return). Stages are gated IN CODE exactly as pre-registered:
DISCOVERY -> VALIDATION -> (combo defined) -> TEST (single look) -> HOLDOUT (single look)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import panel as PB  # noqa: E402
from qpl.data import futures_panel as FP  # noqa: E402
from qpl.research import factory as F, v6  # noqa: E402
from qpl.strategies import futures_factors as FF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/v6_futures_protocol.json"
PR = v6.protocol("v6_futures_protocol.json")
PER = PR["periods"]
GEN = 13

P = FP.build()
U, utab = FP.universe(P)
ret, cost, carry_y = P["ret"][U].loc["1970-01-01":], P["cost"][U], P["carry"][U]
classes = utab.loc[U, "asset_class"]
SIG = PB.sigma(ret)
print("universe", len(U), ret.index[0].date(), ret.index[-1].date())


def bt(sig_df, cm=1.0):
    return PB.run(ret, sig_df, cost, cost_mult=cm, sig=SIG)


bench = bt(FF.long_rp(ret))["net"]
FAM = {
    "F0_CT1_TRANSFER": ("trend/crypto-transfer", lambda: FF.ct1_transfer(ret),
                        {f"leg_{g}": (lambda g=g: FF.ct1_transfer(ret, (g,))) for g in ("t20", "t60", "t120", "d20", "d55")}),
    "F1_TSMOM": ("trend/time-series momentum", lambda: FF.tsmom(ret),
                 {f"L{L}": (lambda L=L: FF.tsmom(ret, (L,))) for L in (21, 63, 126, 252)}),
    "F2_EWMAC": ("trend/EWMA crossover", lambda: FF.ewmac(ret),
                 {f"ewmac{f}_{s}": (lambda f=f, s=s: FF.ewmac(ret, ((f, s),))) for f, s in ((8, 32), (16, 64), (32, 128), (64, 256))}),
    "F3_CARRY": ("carry", lambda: FF.carry(ret, carry_y, 21),
                 {f"smooth{k}": (lambda k=k: FF.carry(ret, carry_y, k)) for k in (1, 63)}),
    "F4_XS_MOM": ("cross-sectional momentum", lambda: FF.xs_momentum(ret, classes, 252),
                  {"lb126": lambda: FF.xs_momentum(ret, classes, 126)}),
    "F5_XS_VALUE": ("cross-sectional value (5y reversal)", lambda: FF.xs_value(ret, classes, 1260, 252),
                    {"w756": lambda: FF.xs_value(ret, classes, 756, 252)}),
    "F6_SKEW": ("cross-sectional skewness", lambda: FF.xs_skew(ret, classes, 252),
                {"skew126": lambda: FF.xs_skew(ret, classes, 126)}),
}
out = {"universe_n": len(U), "benchmark": {}, "families": {}}
for k in ("DISCOVERY", "VALIDATION"):
    out["benchmark"][k] = v6.metrics(bt(FF.long_rp(ret)), None, *PER[k])
signals = {}
for fid, (fam, prim, neigh) in FAM.items():
    h = F.Hypothesis(fid, f"futures/{fam}", PR["families"][fid]["primary"], PR["families"][fid].get("source", "see protocol"),
                     PR["gates"]["DISCOVERY"], "pysystemtrade futures panel", json.dumps(list(neigh)), "LONG_RP", PROTO, generation=GEN)
    h.register()
    s = prim(); signals[fid] = s
    d, d2 = bt(s), bt(s, 2.0)
    res = {"DISCOVERY": v6.metrics(d, bench, *PER["DISCOVERY"], d2), "neighbours": {}}
    v6.record(fid, h.family, "primary", {}, "DISCOVERY", res["DISCOVERY"], GEN, PROTO, "futures panel")
    for nm, fn in neigh.items():
        m = v6.metrics(bt(fn()), bench, *PER["DISCOVERY"])
        res["neighbours"][nm] = m
        v6.record(fid, h.family, nm, {}, "DISCOVERY", m, GEN, PROTO, "futures panel")
    disc = res["DISCOVERY"]
    share = np.mean([m["sharpe"] > 0 for m in res["neighbours"].values()])
    res["disc_pass"] = bool(disc["sharpe"] >= 0.4 and disc["residual_sharpe"] >= 0.2 and share >= 0.7)
    if res["disc_pass"]:
        res["VALIDATION"] = v6.metrics(d, bench, *PER["VALIDATION"], d2)
        v6.record(fid, h.family, "primary", {}, "VALIDATION", res["VALIDATION"], GEN, PROTO, "futures panel")
        res["val_pass"] = bool(res["VALIDATION"]["sharpe"] >= 0.3 and res["VALIDATION"]["residual_sharpe"] > 0)
    res["_d"], res["_d2"] = d, d2
    out["families"][fid] = res
    print(fid, "DISC", round(disc["sharpe"], 2), "resid", round(disc["residual_sharpe"], 2), "nb+", share, "->", res["disc_pass"],
          "| VAL", round(res.get("VALIDATION", {}).get("sharpe", np.nan), 2), res.get("val_pass"))

# Holm across family primaries (DISCOVERY)
out["holm_discovery"] = v6.holm({f: r["DISCOVERY"]["nw_p_one_sided"] for f, r in out["families"].items()})

# F7 combo: equal-risk average of families passing VALIDATION (rule fixed in protocol)
surv = [f for f, r in out["families"].items() if r.get("val_pass")]
out["combo_members"] = surv
fams_eval = list(surv)
if len(surv) >= 2:
    combo = sum(signals[f].fillna(0) for f in surv) / len(surv)
    combo = combo.where(ret.notna().cumsum() > 0)
    signals["F7_COMBO"] = combo
    h = F.Hypothesis("F7_COMBO", "futures/multi-factor", f"equal-risk combo of {surv}", "diversification across premia", PR["gates"]["TEST"],
                     "pysystemtrade futures panel", "n/a", "LONG_RP", PROTO, generation=GEN)
    h.register()
    d, d2 = bt(combo), bt(combo, 2.0)
    out["families"]["F7_COMBO"] = {"DISCOVERY": v6.metrics(d, bench, *PER["DISCOVERY"], d2), "VALIDATION": v6.metrics(d, bench, *PER["VALIDATION"], d2),
                                   "disc_pass": True, "val_pass": True, "_d": d, "_d2": d2}
    for k in ("DISCOVERY", "VALIDATION"):
        v6.record("F7_COMBO", h.family, "primary", {}, k, out["families"]["F7_COMBO"][k], GEN, PROTO, "futures panel")
    fams_eval.append("F7_COMBO")
# Correlations between family P&L (DISCOVERY+VALIDATION) - informational
pn = pd.DataFrame({f: out["families"][f]["_d"]["net"] for f in out["families"]}).loc[PER["DISCOVERY"][0]:PER["VALIDATION"][1]]
out["corr_dev"] = pn.corr().round(2).to_dict()

# TEST (single look) and HOLDOUT (single look) for families that passed VALIDATION (+ combo)
for f in fams_eval:
    r = out["families"][f]
    r["TEST"] = v6.metrics(r["_d"], bench, *PER["TEST"], r["_d2"])
    v6.record(f, "futures", "primary", {}, "TEST_LOOK", r["TEST"], GEN, PROTO, "futures panel")
    t = r["TEST"]
    r["test_pass"] = bool(t["sharpe"] > 0 and t["residual_sharpe"] > 0 and t["net_sharpe_2x_cost"] > 0)
    if r["test_pass"]:
        r["HOLDOUT"] = v6.metrics(r["_d"], bench, *PER["HOLDOUT"], r["_d2"])
        v6.record(f, "futures", "primary", {}, "HOLDOUT_LOOK", r["HOLDOUT"], GEN, PROTO, "futures panel")
        hh = r["HOLDOUT"]
        r["holdout_pass"] = bool(hh["sharpe"] > 0 and hh["residual_sharpe"] > 0 and hh["net_sharpe_2x_cost"] > 0)
    print(f, "TEST", round(t["sharpe"], 2), "resid", round(t["residual_sharpe"], 2), r["test_pass"],
          "| HOLDOUT", round(r.get("HOLDOUT", {}).get("sharpe", np.nan), 2), r.get("holdout_pass"))

for k in ("TEST", "HOLDOUT"):
    out["benchmark"][k] = v6.metrics(bt(FF.long_rp(ret)), None, *PER[k])
# decisions
for f, r in out["families"].items():
    if not r.get("disc_pass"):
        v = "REJECTED"
    elif not r.get("val_pass"):
        v = "EXPLORATORY"
    elif not r.get("test_pass") or not r.get("holdout_pass"):
        v = "PROMISING_BUT_UNVALIDATED"
    else:
        v = "ELIGIBLE_FOR_INDEPENDENT_VALIDATION"
    r["verdict"] = v
    summ = {k: round(r[k]["sharpe"], 2) for k in ("DISCOVERY", "VALIDATION", "TEST", "HOLDOUT") if k in r}
    F.decide(F.Hypothesis(f, "futures", "", "", "", "", "", "", PROTO, generation=GEN), v, f"gen13 net Sharpe by stage {summ}", {"protocol": PROTO})
# save daily P&L for later portfolio work, and results
pnl = pd.DataFrame({f: r["_d"]["net"] for f, r in out["families"].items()})
pnl["LONG_RP"] = bench
pnl.to_parquet(ROOT / "results/v6_futures_gen13_pnl.parquet")
for r in out["families"].values():
    r.pop("_d", None); r.pop("_d2", None)
(ROOT / "results/v6_futures_gen13.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps({f: r["verdict"] for f, r in out["families"].items()}, indent=1))
print("holm", out["holm_discovery"])

"""V6 gen18: crypto XS 7-day continuation with 4-weekly rebalancing (protocol config/v6_gen18_protocol.json)."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.data import coinmetrics as CM
from qpl.research import factory as F, v6
ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/v6_gen18_protocol.json"
P = CM.load(); bt = CM.XSBacktester(P); lr = np.log(P["PriceUSD"])
VAL, TEST = ("2021-01-01", "2022-12-31"), ("2023-01-01", "2026-05-24")
s7, s14 = lr - lr.shift(7), lr - lr.shift(14)
prim = bt.run(s7, every=4)
neigh = {"every2": bt.run(s7, every=2), "sig14_every4": bt.run(s14, every=4)}
out = {"VALIDATION": {"net": CM.sharpe_w(prim.loc[VAL[0]:VAL[1], "net"]), "gross": CM.sharpe_w(prim.loc[VAL[0]:VAL[1], "gross"]),
                      "turn_wk": float(prim.loc[VAL[0]:VAL[1], "turn"].mean())},
       "neighbours_VAL": {k: CM.sharpe_w(v.loc[VAL[0]:VAL[1], "net"]) for k, v in neigh.items()},
       "TRAIN_info_only": CM.sharpe_w(prim.loc["2017-07-01":"2020-12-31", "net"])}
out["val_pass"] = bool(out["VALIDATION"]["net"] >= 0.3 and np.mean([v > 0 for v in out["neighbours_VAL"].values()]) >= 0.5)
h = F.Hypothesis("H18_XS_CONTINUATION_LOWTURN", "crypto/cross-section", "7-day XS continuation, 4-weekly rebalance", "attention/flow persistence at weekly horizon",
                 "VALIDATION net < 0.3", "Coin Metrics community", "every 2/4 weeks; 7/14-day signal", "zero", PROTO, generation=18)
h.register()
v6.record(h.id, h.family, "primary", {}, "VALIDATION", out["VALIDATION"] | {"neighbours": out["neighbours_VAL"]}, 18, PROTO, "crypto XS")
if out["val_pass"]:
    p60 = bt.run(s7, every=4, cost_bps=60.0)
    out["TEST"] = {"net": CM.sharpe_w(prim.loc[TEST[0]:TEST[1], "net"]), "net60": CM.sharpe_w(p60.loc[TEST[0]:TEST[1], "net"]),
                   "gross": CM.sharpe_w(prim.loc[TEST[0]:TEST[1], "gross"])}
    out["test_pass"] = bool(out["TEST"]["net"] > 0 and out["TEST"]["net60"] > 0)
    v6.record(h.id, h.family, "primary", {}, "TEST_LOOK", out["TEST"], 18, PROTO, "crypto XS")
v = "EXPLORATORY" if not out["val_pass"] else ("PROMISING_BUT_UNVALIDATED" if out.get("test_pass") else "EXPLORATORY")
if not out["val_pass"] and out["VALIDATION"]["net"] < 0:
    v = "REJECTED"
out["verdict"] = v
F.decide(h, v, json.dumps({k: out[k] for k in ("VALIDATION", "TEST") if k in out}), {"protocol": PROTO})
out["by_year_net"] = {int(y): round(float(x), 3) for y, x in prim["net"].groupby(prim.index.year).sum().items()}
(ROOT / "results/v6_gen18_crypto_cont.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1))

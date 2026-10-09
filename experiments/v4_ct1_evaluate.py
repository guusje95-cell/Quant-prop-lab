"""Reproduce every recorded CT1 stage (dev, OOS look, holdout look, cost stress, long-only) WITHOUT recording new
experiments, and compare with results/v4_ct1_holdout.json. Protocol: config/ct1_protocol.json."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.research import crypto_factory as CF, factory as F
ROOT = Path(__file__).resolve().parents[1]
hyp = F.Hypothesis("CT1_TREND_ENSEMBLE", "crypto/trend", "", "", "", "", "", "", "", generation=10)
stored = json.loads((ROOT / "results/v4_ct1_holdout.json").read_text())
runs = {"dev": dict(params={}, periods=("train", "validation")), "oos": dict(params={}, periods=("oos",)),
        "7bps": dict(params={}, periods=("holdout",)), "stress15": dict(params={}, periods=("holdout",), cost=15.0),
        "stress21": dict(params={}, periods=("holdout",), cost=21.0), "long_only_secondary": dict(params={"long_only": True}, periods=("holdout",))}
out, ok = {}, True
for k, r in runs.items():
    cost = r.get("cost")
    if cost:
        CF.COSTS["_stress"] = cost
    res = CF.evaluate(hyp, "trend_ensemble", r["params"], "1D", r["periods"], cost="_stress" if cost else "perp_taker", record=False)
    out[k] = {p: {m: round(v[m], 4) for m in ("sharpe", "residual_sharpe", "max_dd")} for p, v in res["periods"].items()}
    if k in stored:
        d = abs(stored[k]["sharpe"] - res["periods"]["holdout"]["sharpe"])
        out[k]["matches_stored"] = bool(d < 1e-9); ok &= d < 1e-9
(ROOT / "results/v4_ct1_repro.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1)); print("REPRODUCED" if ok else "MISMATCH")

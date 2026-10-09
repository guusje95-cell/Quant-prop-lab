"""CT1 vs generic crypto-allowed evaluation rules (UNCERTAIN parameters, config/prop_firms_v4_crypto.json).
Bootstrap of post-development CT1 daily returns (2022-2026, realized labels). Daily loss checked on close-to-close
daily P&L only (intraday excursions NOT modelled -> breach probabilities are LOWER BOUNDS)."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB
from qpl.data import crypto as CD
from qpl.research import crypto_factory as CF
from qpl.statistics import tests as T
from qpl.strategies import crypto as CS
ROOT = Path(__file__).resolve().parents[1]
b = CD.btc_bars("1D").loc["2014-06-01":]
f, _ = CF.btc_funding()
r = VB.daily(VB.run(b, CS.trend_ensemble(b, {}), 7.0, f), at="realized")["net"].loc["2022-01-01":"2026-10-08"].to_numpy()
RULES = {"FTMO_swing_phase1": dict(target=0.10, max_loss=0.10, daily=0.05), "FTMO_swing_phase2": dict(target=0.05, max_loss=0.10, daily=0.05),
         "HyroTrader_like": dict(target=0.10, max_loss=0.06, daily=0.04), "Breakout_like_6pct": dict(target=0.10, max_loss=0.06, daily=0.03)}
def sim(r, scale, target, max_loss, daily, horizon=365, n=4000, extra_cost=0.0, seed=3):
    ii = T.stationary_bootstrap_indices(len(r), n, 20, np.random.default_rng(seed))[:, :horizon]
    P = r[ii] * scale - extra_cost / 365
    eq = np.cumsum(P, axis=1)
    res = {"pass": 0, "fail_max": 0, "fail_daily": 0, "open": 0}
    days = []
    for k in range(n):
        hit_t = np.argmax(eq[k] >= target) if (eq[k] >= target).any() else horizon
        hit_m = np.argmax(eq[k] <= -max_loss) if (eq[k] <= -max_loss).any() else horizon
        hit_d = np.argmax(P[k] <= -daily) if (P[k] <= -daily).any() else horizon
        first = min(hit_t, hit_m, hit_d)
        if first == horizon: res["open"] += 1
        elif first == hit_t and hit_t < min(hit_m, hit_d): res["pass"] += 1; days.append(hit_t + 1)
        elif first == hit_d: res["fail_daily"] += 1
        else: res["fail_max"] += 1
    out = {k: v / n for k, v in res.items()}
    out["median_days_to_pass"] = float(np.median(days)) if days else None
    return out
out = {"note": __doc__, "results": {}}
for name, R in RULES.items():
    for scale in (0.15, 0.25, 0.40, 0.60):
        for cost in (0.0, 0.10, 0.20):
            if cost and not name.startswith("FTMO"):
                continue
            out["results"][f"{name}|scale{scale}|fin{cost}"] = sim(r, scale, **R, extra_cost=cost)
(ROOT / "results/v4_ct1_prop_crypto.json").write_text(json.dumps(out, indent=1))
for k, v in out["results"].items():
    print(k, {a: (round(x, 3) if isinstance(x, float) else x) for a, x in v.items()})

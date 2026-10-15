"""Gen67 stress tests (config/gen67_protocol.json). Writes results/gen67_stress.csv and results/gen67_stress_prop.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import propfirms as PF
src = (ROOT / "scripts/gen66_prop_tools.py").read_text().split("FIRMS = [")[0]
g = {"__file__": str(ROOT / "scripts/gen66_prop_tools.py"), "__name__": "g66"}; exec(compile(src, "g66", "exec"), g)
port, to_daily_stop = g["port"], g["to_daily_stop"]

rng = np.random.default_rng(7)
rows = []
for name, stop in (("no stop", 0.0), ("S50 at a 4% daily limit (stop at -2%)", 0.02)):
    d = to_daily_stop(port, stop)["net"].to_numpy(); n = len(d)
    ann, mdd, wm, neg = [], [], [], 0
    for _ in range(2000):
        idx = []
        while len(idx) < 365:
            s = rng.integers(n); idx.extend(range(s, min(s + 20, n)))
        x = d[np.array(idx[:365])]
        eq = np.cumprod(1 + x); ann.append(eq[-1] - 1); mdd.append((eq / np.maximum.accumulate(eq) - 1).min())
        m = [np.prod(1 + x[i:i + 30]) - 1 for i in range(0, 360, 30)]; wm.append(min(m))
    ann, mdd, wm = map(np.array, (ann, mdd, wm))
    rows.append({"variant": name, "median_year": np.median(ann), "p5_year": np.percentile(ann, 5), "p1_year": np.percentile(ann, 1),
                 "P_losing_year": (ann < 0).mean(), "median_maxdd": np.median(mdd), "p5_maxdd": np.percentile(mdd, 5), "p1_maxdd": np.percentile(mdd, 1),
                 "median_worst_month": np.median(wm), "p5_worst_month": np.percentile(wm, 5)})
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen67_stress.csv", index=False)

prop = []
for key in ("HyroTrader One-Step $100k", "Crypto Fund Trader 1-Phase $100k"):
    f = PF.PRESETS[key]; lim = f.daily_loss
    hc, hf = to_daily_stop(port, 0.5 * lim), to_daily_stop(port * 0.6, 0.5 * lim)
    for method in ("historical", "bootstrap"):
        p = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5, method=method, n_boot=1000, block=20, seed=11)
        prop.append({"firm": f.name, "paths": method, "n": p["n"], "P_funded": p["P_funded"], "net_mean": p["net_mean"], "net_p10": p["net_p10"],
                     "net_p50": p["net_p50"], "net_p90": p["net_p90"], "P_profit": p["P_profit"], "P_lose_all_budget": p["P_lose_all_budget"]})
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in prop[-1].items()}, flush=True)
pd.DataFrame(prop).to_csv(ROOT / "results/gen67_stress_prop.csv", index=False)

"""Gen69 M7: prop sizing for portfolio v4 (C* + premium carry + strict-limit cascade + 4h trend, equal risk, vol targeting 30d),
S50 daily stop, bootstrap 500 paths. Descriptive (selected on the same data). Writes results/gen69_prop_sizing.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen55_firms as G55
from qpl.lab import propfirms as PF


def to_daily_stop(h, stop):
    rows = []
    for d, gg in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + gg.to_numpy())
        if stop > 0 and (p <= 1 - stop).any():
            k = int(np.argmax(p <= 1 - stop)); close = p[k] - 0.001
            rows.append((d, close - 1, min(p[:k + 1].min(), close) - 1, max(p[:k + 1].max(), 1.0) - 1))
        else:
            rows.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day")


v4 = CS.portfolio_v3(cols=("C*", "premium carry", "cascade limit strict", "trend 4h"))
rows = []
for key in ("HyroTrader One-Step $100k", "HyroTrader Two-Step $100k", "SizeProp One-Step $100k", "Crypto Fund Trader 1-Phase $100k"):
    f = PF.PRESETS[key]
    for sc in (0.75, 1.0, 1.25):
        hc = to_daily_stop(v4 * sc, 0.5 * f.daily_loss)
        for sf in (0.4, 0.6, 0.8):
            hf = to_daily_stop(v4 * sf, 0.5 * f.daily_loss)
            a = PF.attempts(hc, f, 1.0)
            pb = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
            mi, am = G55.months_with_income(hc, hf, f)
            rows.append({"firm": f.name, "risk_challenge": sc, "risk_funded": sf, "pass": a["P_pass"], "days_to_pass": a["median_days_to_pass"],
                         "boot_net": pb["net_mean"], "boot_p10": pb["net_p10"], "boot_p50": pb["net_p50"], "boot_p_profit": pb["P_profit"],
                         "months_with_income": mi, "avg_month": am})
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen69_prop_sizing.csv", index=False)

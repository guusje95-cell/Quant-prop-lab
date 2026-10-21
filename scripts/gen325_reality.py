"""Gen325 (descriptive, config/gen325_protocol.json): how much of the backtest Sharpe to believe, and what running both accounts
together looks like.
  1. Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) of v8.6 and bf2.6 for N = 50 / 300 / 1559 trials (1559 = every trial
     registered in this project), with the returns' skewness and kurtosis; the expected best-of-N null Sharpe SR0 gives a
     "planning Sharpe" = backtest Sharpe - SR0.
  2. Joint prop simulation: HyroTrader 2-Step $200k (v8.6) and BrightFunded Classic $200k swap-free (bf2.6) on the SAME
     block-bootstrap day paths (their correlation is kept), challenge risk 2.0 / funded 1.5, daily stop at half the limit,
     up to 5 challenges each, 730 days. Run on the backtest returns and on returns scaled down to the planning Sharpe.
Writes results/gen325.json."""
import json
import sys
from dataclasses import replace
from math import e
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
HY = PF.PRESETS["HyroTrader Two-Step $200k"]; BF = PF.PRESETS["BrightFunded Two-Step Classic $200k"]; BF = replace(BF, fee=BF.fee + 0.1 * BF.fee)
BOOKS = {"v8.6": ("v86", HY), "bf2.6": ("bf26", BF)}
H = {k: pd.read_parquet(ROOT / f"results/cache_{f}_final.parquet")["portfolio"].loc["2022-01-01":"2026-09-30 23:00"] for k, (f, _) in BOOKS.items()}
out = {}

# ---- 1. deflated Sharpe ---------------------------------------------------------------------------------------------------
gamma = 0.5772156649
for k, h in H.items():
    d = h.groupby(h.index.floor("D")).sum(); T = len(d); sr = d.mean() / d.std(); g3, g4 = skew(d), kurtosis(d, fisher=False)
    res = {"backtest Sharpe (annual)": round(float(sr * np.sqrt(365)), 3), "days": T, "skew": round(float(g3), 2), "kurtosis": round(float(g4), 2)}
    for N in (50, 300, 1559):
        sr0 = np.sqrt(1.0 / T) * ((1 - gamma) * norm.ppf(1 - 1 / N) + gamma * norm.ppf(1 - 1 / (N * e)))
        dsr = norm.cdf((sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
        res[f"N={N}"] = {"SR0 (annual)": round(float(sr0 * np.sqrt(365)), 3), "DSR (prob. true Sharpe > 0)": round(float(dsr), 4),
                         "planning Sharpe = SR - SR0": round(float((sr - sr0) * np.sqrt(365)), 3)}
    out[k] = res; print(k, res, flush=True)

# ---- 2. joint prop simulation --------------------------------------------------------------------------------------------
def deflate(h, target):
    """subtract a constant per hour so the 2022-26 annual Sharpe of the daily sums equals `target` (volatility unchanged)."""
    d = h.groupby(h.index.floor("D")).sum(); m_t = target * d.std() / np.sqrt(365)
    return h - (d.mean() - m_t) / 24


def joint(series, sample_start, label):
    days = {}
    for k, (f, firm) in BOOKS.items():
        x = series[k].loc[sample_start:]
        days[k] = (to_daily_stop(x * 2.0, 0.5 * firm.daily_loss), to_daily_stop(x * 1.5, 0.5 * firm.daily_loss), firm)
    common = days["v8.6"][0].index.intersection(days["bf2.6"][0].index)
    paths, cal0 = PF._paths(days["v8.6"][0].loc[common], "bootstrap", 730, 5, 500, 20, 11)
    per_day = len(common) / max(1, cal0[-1]); nets = {}
    for k, (dc, df, firm) in days.items():
        rc0, loc0, hic0 = PF._arrays(dc.loc[common], 1.0); rf0, lof0, hif0 = PF._arrays(df.loc[common], 1.0); nets[k] = []
        for _, x in paths:
            cal = (np.arange(len(x)) / per_day).astype(int)
            nets[k].append(PF._ledger(rc0[x], loc0[x], hic0[x], rf0[x], lof0[x], hif0[x], cal, 0, len(x), firm, 5)["net"])
        nets[k] = np.array(nets[k])
    a, b = nets["v8.6"], nets["bf2.6"]; tot = a + b
    dv = series["v8.6"].loc[sample_start:]; db = series["bf2.6"].loc[sample_start:]
    corr = float(pd.concat([dv.groupby(dv.index.floor("D")).sum(), db.groupby(db.index.floor("D")).sum()], axis=1).corr().iloc[0, 1])
    r = {"daily return correlation": round(corr, 3),
         "HyroTrader v8.6 net: mean / p10 / P(loss)": [round(float(a.mean())), round(float(np.percentile(a, 10))), round(float((a < 0).mean()), 3)],
         "BrightFunded bf2.6 net: mean / p10 / P(loss)": [round(float(b.mean())), round(float(np.percentile(b, 10))), round(float((b < 0).mean()), 3)],
         "both accounts: mean / p10 / p50 / p90": [round(float(tot.mean())), round(float(np.percentile(tot, 10))), round(float(np.percentile(tot, 50))), round(float(np.percentile(tot, 90)))],
         "P(both lose money)": round(float(((a < 0) & (b < 0)).mean()), 3), "P(combined loss)": round(float((tot < 0).mean()), 3),
         "combined per month (mean)": round(float(tot.mean() / 24))}
    out[label] = r; print(label, r, flush=True)


for smp in ("2023-01-01", "2025-01-01"):
    joint(H, smp, f"joint, backtest returns, sample {smp[:4]}-26")
for N in (300,):
    plan = {k: deflate(h, out[k][f"N={N}"]["planning Sharpe = SR - SR0"]) for k, h in H.items()}
    for smp in ("2023-01-01", "2025-01-01"):
        joint(plan, smp, f"joint, planning Sharpe (N={N}), sample {smp[:4]}-26")
half = {k: deflate(h, out[k]["backtest Sharpe (annual)"] / 2) for k, h in H.items()}
joint(half, "2025-01-01", "joint, half the backtest Sharpe (Harvey-Liu-style 50% haircut), sample 2025-26")
json.dump(out, open(ROOT / "results/gen325.json", "w"), indent=1)

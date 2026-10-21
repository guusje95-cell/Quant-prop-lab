"""Book comparison v5 -> v8.4 and bf -> bf2.2 (descriptive): statistics, equity curves, monthly returns, prop-firm bootstrap.
Point-in-time hourly book series (results/cache_*), each scaled to 15% vol over 2022-26 (risk 1.0). CFD books all at the measured
BrightFunded spreads (bf, bf2: paper_v5.py _dump with QPL_MEASURED_COSTS=1). Writes results/compare/*.csv."""
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
OUT = ROOT / "results/compare"; OUT.mkdir(parents=True, exist_ok=True)
HY, BF = PF.PRESETS["HyroTrader Two-Step $200k"], PF.PRESETS["BrightFunded Two-Step Classic $200k"]
BF = replace(BF, fee=BF.fee + 96.0)                                     # swap-free add-on
BOOKS = [("v5", "Crypto", "gen72", "Gen72 base: C*, premium carry, cascade, trend 4h, Weiss expiry"),
         ("v6", "Crypto", "v6", "v5 + deleveraging bounce"),
         ("v7", "Crypto", "v7", "v6 + ridge ML"),
         ("v8", "Crypto", "v8", "v7 + altcoin kimchi premium"),
         ("v8.3", "Crypto", "v83", "v8 + kimchi breadth, vol-scaled ridge, inverse-vol carry"),
         ("v8.4", "Crypto", "v84", "v8.3 + spot flow, variance risk premium and weekend features in the ridge"),
         ("v8.5", "Crypto", "v85", "v8.4 + premium carry on 60 coins with inverse-vol legs (added sleeve)"),
         ("bf", "CFD", "bf_measured", "crypto CFD book: C*, carry, trend, Weiss, delev bounce, Coinbase premium"),
         ("bf2", "CFD", "bf2_measured", "bf + ridge ML + index CFDs (US100/US500/US30)"),
         ("bf2.2", "CFD", "bf22", "bf2 + spot flow, variance risk premium and weekend features in the ridge"),
         ("bf2.3", "CFD", "bf23", "bf2.2 + altcoin kimchi premium on 14 altcoin CFDs"),
         ("bf2.4", "CFD", "bf24", "bf2.3 + premium carry on 35 crypto CFDs with inverse-vol legs (added sleeve)")]
P = [("2022-26", "2022-01-01", "2026-09-30"), ("2022", "2022-01-01", "2022-12-31"), ("2023-24", "2023-01-01", "2024-12-31"), ("2025-26", "2025-01-01", "2026-09-30")]
stats, eq, mon, prop = [], [], [], []
for name, fam, f, what in BOOKS:
    h = pd.read_parquet(ROOT / f"results/cache_{f}.parquet" if "measured" in f else ROOT / f"results/cache_{f}_final.parquet")["portfolio"]
    h = h.loc["2022-01-01":"2026-09-30 23:00"]; d = h.groupby(h.index.floor("D")).sum()
    k = 0.15 / (d.std() * np.sqrt(365)); h, d = h * k, d * k
    sh = {p: d.loc[a:z].mean() / d.loc[a:z].std() * np.sqrt(365) for p, a, z in P}
    w = (1 + d).cumprod(); dd = w / w.cummax() - 1; yrs = len(d) / 365
    m = (1 + d).groupby(d.index.to_period("M")).prod() - 1
    under = (dd < 0).astype(int); runs = under.groupby((under == 0).cumsum()).sum()
    down = d[d < 0]
    stats.append({"book": name, "family": fam, "what": what, "sharpe": sh["2022-26"], "sharpe_2022": sh["2022"], "sharpe_2023_24": sh["2023-24"],
                  "sharpe_2025_26": sh["2025-26"], "cagr": w.iloc[-1] ** (1 / yrs) - 1, "vol": d.std() * np.sqrt(365), "max_dd": dd.min(),
                  "calmar": (w.iloc[-1] ** (1 / yrs) - 1) / -dd.min(), "sortino": d.mean() / np.sqrt((down ** 2).sum() / len(d)) * np.sqrt(365),
                  "pos_months": (m > 0).mean(), "months": len(m), "best_month": m.max(), "worst_month": m.min(), "pos_days": (d > 0).mean(),
                  "worst_day": d.min(), "longest_dd_days": int(runs.max()), "total_return": w.iloc[-1] - 1})
    ws = w.resample("W-SUN").last(); dds = dd.resample("W-SUN").min()
    eq += [{"book": name, "week": t.strftime("%Y-%m-%d"), "equity": float(v), "drawdown": float(dds[t])} for t, v in ws.items()]
    mon += [{"book": name, "month": str(p), "ret": float(v)} for p, v in m.items()]
    firm, fname = (HY, "HyroTrader 2-Step $200k") if fam == "Crypto" else (BF, "BrightFunded Classic $200k")
    for per, a in (("2023-26", "2023-01-01"), ("2025-26", "2025-01-01")):
        x = h.loc[a:"2026-09-30 23:00"]
        pb = PF.pipeline(to_daily_stop(x * 2.0, 0.5 * firm.daily_loss), firm, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.5 * firm.daily_loss),
                         horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
        prop.append({"book": name, "family": fam, "firm": fname, "sample": per, "net_mean": pb["net_mean"], "net_p10": pb["net_p10"], "net_p50": pb["net_p50"],
                     "net_p90": pb["net_p90"], "net_per_month": pb["net_per_month"], "p_profit": pb["P_profit"], "p_funded": pb["P_funded"],
                     "days_to_funded": pb["days_to_funded_median"], "fees": pb["fees"], "challenges_bought": pb["bought"]})
    print(name, round(sh["2022-26"], 3), flush=True)
for nm, rows in (("stats", stats), ("equity", eq), ("monthly", mon), ("prop", prop)):
    pd.DataFrame(rows).to_csv(OUT / f"{nm}.csv", index=False, float_format="%.6g")
print(pd.DataFrame(stats).drop(columns="what").round(3).to_string()); print(pd.DataFrame(prop).round(3).to_string())

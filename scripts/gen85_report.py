"""Gen85 adopted CFD book (swap-aware C* thr 0.5 + Weiss): stats and prop sims vs the old book. Writes results/gen85_stats.csv,
results/gen85_prop.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import propfirms as PF
C = pd.read_parquet(ROOT / "results/cache_gen85_hourly.parquet")
H83 = pd.read_parquet(ROOT / "results/cache_gen83_hourly.parquet")


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


W = C["ref Weiss BTC/ETH"]
books = {"NEW CFD book (swap-aware C* + Weiss)": CS.portfolio_v5(pd.DataFrame({"C*": C["B1 swap-aware C* thr 0.5"], "Weiss expiry": W}).fillna(0))[0],
         "old CFD book (C* + Weiss)": CS.portfolio_v5(pd.DataFrame({"C*": C["ref C* CFD"], "Weiss expiry": W}).fillna(0))[0],
         "swap-free book (Gen83)": H83["swap-free book (4 sleeves)"]}
rows = []
for n, h in books.items():
    d = h.groupby(h.index.floor("D")).sum().loc["2022-01-01":"2026-09-30"]; x = d * 0.15 / (d.std() * np.sqrt(365))
    eq = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1; y = (1 + x).resample("YE").prod() - 1
    rows.append({"book": n, "Sharpe": x.mean() / x.std() * np.sqrt(365), "CAGR@15%vol": eq.iloc[-1] ** (365 / len(x)) - 1,
                 "MaxDD": (eq / eq.cummax() - 1).min(), "pos months": (m > 0).mean(), "worst month": m.min(), **{str(k.year): v for k, v in y.items()}})
S = pd.DataFrame(rows); S.to_csv(ROOT / "results/gen85_stats.csv", index=False); pd.set_option("display.width", 250); print(S.round(3).to_string(), flush=True)
P = []
for n in list(books)[:2]:
    h = books[n].loc["2022-01-01":"2026-09-30 23:00"]; dd = h.groupby(h.index.floor("D")).sum(); h = h * 0.15 / (dd.std() * np.sqrt(365))
    for key in ("FTMO 2-Step $100k", "FundedNext Stellar 2-Step $100k", "BrightFunded Two-Step Classic $100k"):
        f = PF.PRESETS[key]
        for sc, sf, st in ((1.0, 0.6, 0.5), (1.5, 1.0, 0.6)):
            hc = to_daily_stop(h * sc, st * f.daily_loss); hf = to_daily_stop(h * sf, st * f.daily_loss)
            a = PF.attempts(hc, f, 1.0)
            pb = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
            P.append({"book": n, "firm": f.name, "setting": f"{sc}/{sf}/{st}", "pass": a["P_pass"], "days_to_pass": a["median_days_to_pass"],
                      "mean_net": pb["net_mean"], "p10": pb["net_p10"], "P_profit": pb["P_profit"]})
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in P[-1].items()}, flush=True)
pd.DataFrame(P).to_csv(ROOT / "results/gen85_prop.csv", index=False)
print("done", flush=True)

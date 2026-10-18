"""Gen83 (config/gen83_protocol.json): swap-free CFD book. Reuses the Gen74 sleeve builders. Writes results/gen83_*.csv,
results/cache_gen83_hourly.parquet and results/gen83_swapfree.png."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen74_crypto_cfd.py").read().split('SCEN = {')[0]          # builders + positions only
ns = {"__file__": str(ROOT / "scripts/gen74_crypto_cfd.py")}; exec(compile(src, "gen74_builders", "exec"), ns)
CS, PF, G55 = ns["CS"], ns["PF"], ns["G55"]

SLEEVES = ["C*", "premium carry", "trend 4h", "Weiss expiry"]
H0 = ns["sleeves"](0.0, 1.0)[SLEEVES]; H2 = ns["sleeves"](0.0, 2.0)[SLEEVES]
Hb = ns["sleeves"](3.3, 1.0)[["C*", "Weiss expiry"]]
books = {"swap-free book (4 sleeves)": CS.portfolio_v5(H0)[0], "swap-free book, 2x spread": CS.portfolio_v5(H2)[0],
         "base CFD book (C* + Weiss, swap 3.3)": CS.portfolio_v5(Hb)[0]}
pd.DataFrame(books).to_parquet(ROOT / "results/cache_gen83_hourly.parquet")


def d15(h):
    d = h.groupby(h.index.floor("D")).sum().loc["2022-01-01":"2026-09-30"]; return d * 0.15 / (d.std() * np.sqrt(365))


rows = []
for n, h in books.items():
    x = d15(h); eq = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1; y = (1 + x).resample("YE").prod() - 1
    rows.append({"book": n, "Sharpe": x.mean() / x.std() * np.sqrt(365), "CAGR": eq.iloc[-1] ** (365 / len(x)) - 1,
                 "MaxDD": (eq / eq.cummax() - 1).min(), "pos months": (m > 0).mean(), "worst month": m.min(),
                 **{str(k.year): v for k, v in y.items()}})
S = pd.DataFrame(rows); S.to_csv(ROOT / "results/gen83_stats.csv", index=False); pd.set_option("display.width", 250); print(S.round(3).to_string())
corr = H0.groupby(H0.index.floor("D")).sum().loc["2022":].corr(); print(corr.round(2))
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
P = []
for n in ("swap-free book (4 sleeves)", "base CFD book (C* + Weiss, swap 3.3)"):
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
pd.DataFrame(P).to_csv(ROOT / "results/gen83_prop.csv", index=False)
print("done", flush=True)

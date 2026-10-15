"""Gen68: portfolio v3 (C* + premium carry + cascade limit with 0.1% trade-through; portfolio vol targeting) - stats, chart,
prop (historical + bootstrap) with S50. Writes results/gen68_portfolio_prop.csv, results/gen68_portfolio_stats.csv, results/gen68_portfolio.png."""
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

v3 = CS.portfolio_v3()
day = lambda h: h.groupby(h.index.floor("D")).sum()
H = CS.all_sleeves(); D = day(H)
def eqrisk(cols):
    z = D[list(cols)].loc["2022-01-01":"2026-09-30"]; z = z / (z.std() * np.sqrt(365)) * 0.10; x = z.mean(axis=1); return x * 0.15 / (x.std() * np.sqrt(365))
series = {"v3: strict fills + vol targeting": day(v3), "v2: limit cascade (touch)": eqrisk(["C*", "premium carry", "cascade limit"]),
          "v1: market cascade": eqrisk(["C*", "premium carry", "cascade"]), "C* alone": eqrisk(["C*"])}
rows = []
for n, x in series.items():
    m = (1 + x).resample("ME").prod() - 1; eq = (1 + x).cumprod(); y = (1 + x).resample("YE").prod() - 1
    rows.append({"portfolio": n, "Sharpe": x.mean() / x.std() * np.sqrt(365), "CAGR": eq.iloc[-1] ** (365 / len(x)) - 1, "Vol": x.std() * np.sqrt(365),
                 "MaxDD": (eq / eq.cummax() - 1).min(), "Positive months": (m > 0).mean(), "Worst month": m.min(), "Worst day": x.min(),
                 **{f"Y{d.year}": v for d, v in y.items()}})
st = pd.DataFrame(rows); st.to_csv(ROOT / "results/gen68_portfolio_stats.csv", index=False)
pd.set_option("display.width", 250); print(st.round(3).to_string())

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
for (n, x), col in zip(series.items(), ("#1f4fbf", "#7fa7e8", "#b9c9e6", "#e07b39")):
    eq = (1 + x).cumprod(); ax[0].plot(eq.index, eq, color=col, lw=1.7 if n.startswith("v3") else 1.1, label=f"{n} (Sharpe {x.mean() / x.std() * np.sqrt(365):.2f})")
    ax[1].plot(eq.index, eq / eq.cummax() - 1, color=col, lw=1)
ax[0].set_yscale("log"); ax[0].legend(frameon=False); ax[0].grid(alpha=.25); ax[0].set_ylabel("growth of 1 (log)")
ax[0].set_title("Crypto-firm portfolio, ~15% volatility, 2022-01 to 2026-09 (descriptive)"); ax[1].grid(alpha=.25); ax[1].set_ylabel("drawdown")
fig.tight_layout(); fig.savefig(ROOT / "results/gen68_portfolio.png", dpi=130)

out = []
for key in ("HyroTrader One-Step $100k", "HyroTrader Two-Step $100k", "Crypto Fund Trader 1-Phase $100k", "SizeProp One-Step $100k"):
    f = PF.PRESETS[key]
    hc, hf = to_daily_stop(v3, 0.5 * f.daily_loss), to_daily_stop(v3 * 0.6, 0.5 * f.daily_loss)
    a = PF.attempts(hc, f, 1.0); ph = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5)
    pb = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, method="bootstrap", n_boot=1000, block=20, seed=11)
    mi, am = G55.months_with_income(hc, hf, f)
    out.append({"firm": f.name, "pass": a["P_pass"], "fail_daily": a["P_fail_daily"], "hist_net": ph["net_mean"], "hist_p10": ph["net_p10"],
                "boot_net": pb["net_mean"], "boot_p10": pb["net_p10"], "boot_p_profit": pb["P_profit"], "months_with_income": mi, "avg_month": am})
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[-1].items()}, flush=True)
pd.DataFrame(out).to_csv(ROOT / "results/gen68_portfolio_prop.csv", index=False)

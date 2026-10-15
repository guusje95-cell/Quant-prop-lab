"""Crypto portfolio (descriptive): C* + funding carry + cascade + ETH evening, each sleeve scaled to 10% vol, equal weight, portfolio
scaled to 15% vol (same risk as C* in the challenge). Equity curve, statistics, and prop-firm simulation on the hourly path
(2022-01..2026-09, all sleeves live). Writes results/gen58_crypto_portfolio_*.csv and results/gen58_crypto_portfolio.png."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import propfirms as PF

H = CS.all_sleeves()
D = H.groupby(H.index.floor("D")).sum()
live = {"C*": "2020-03-01", "funding carry": "2020-03-01", "premium carry": "2020-03-01", "cascade": "2022-01-01", "ETH evening": "2020-03-01"}
SLEEVES = ["C*", "premium carry", "cascade", "ETH evening"]
scale = {c: 0.10 / (D[c].loc[live[c]:].std() * np.sqrt(365)) for c in D}
Hs = H.mul(pd.Series(scale)); Ds = D.mul(pd.Series(scale))
port_h = Hs[SLEEVES].mean(axis=1)
k = 0.15 / (port_h.groupby(port_h.index.floor("D")).sum().loc["2022":].std() * np.sqrt(365))
cst_k = 0.15 / (Ds["C*"].loc["2022":].std() * np.sqrt(365))
series = {"Portfolio (4 sleeves)": port_h * k, "C* alone": Hs["C*"] * cst_k, "3 sleeves (C*, carry, cascade)": Hs[["C*", "premium carry", "cascade"]].mean(axis=1)}
k3 = 0.15 / (series["3 sleeves (C*, carry, cascade)"].groupby(series["3 sleeves (C*, carry, cascade)"].index.floor("D")).sum().loc["2022":].std() * np.sqrt(365))
series["3 sleeves (C*, carry, cascade)"] *= k3
daily = {n: s.groupby(s.index.floor("D")).sum() for n, s in series.items()}


def stats(x):
    m = (1 + x).resample("ME").prod() - 1; yv = (1 + x).resample("YE").prod() - 1
    eq = (1 + x).cumprod(); dd = (eq / eq.cummax() - 1)
    yrs = len(x) / 365
    return {"Sharpe": x.mean() / x.std() * np.sqrt(365), "CAGR": eq.iloc[-1] ** (1 / yrs) - 1, "Volatility": x.std() * np.sqrt(365),
            "Max drawdown": dd.min(), "Calmar": (eq.iloc[-1] ** (1 / yrs) - 1) / -dd.min(), "Positive months": (m > 0).mean(),
            "Avg month": m.mean(), "Worst month": m.min(), "Best month": m.max(), "Worst day": x.min(), "Best day": x.max(),
            "Positive years": (yv > 0).mean(), **{f"Year {y.year}": v for y, v in yv.items()}}


rows = []
for per, a in (("2022-01..2026-09", "2022-01-01"), ("2023-01..2026-09", "2023-01-01")):
    for n, x in daily.items():
        rows.append({"period": per, "portfolio": n, **stats(x.loc[a:"2026-09-30"])})
st = pd.DataFrame(rows); st.to_csv(ROOT / "results/gen58_crypto_portfolio_stats.csv", index=False)
print(st[["period", "portfolio", "Sharpe", "CAGR", "Max drawdown", "Positive months", "Worst month", "Worst day"]].round(3).to_string())
corr = Ds[SLEEVES].loc["2022":].corr(); print(corr.round(2))
mt = ((1 + daily["Portfolio (4 sleeves)"].loc["2022":]).resample("ME").prod() - 1)
mt.to_frame("return").to_csv(ROOT / "results/gen58_crypto_portfolio_monthly.csv")

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
for n, col in (("Portfolio (4 sleeves)", "#2a6fdb"), ("3 sleeves (C*, carry, cascade)", "#7fa7e8"), ("C* alone", "#e07b39")):
    x = daily[n].loc["2022":]; eq = (1 + x).cumprod()
    ax[0].plot(eq.index, eq, label=f"{n}  (Sharpe {x.mean() / x.std() * np.sqrt(365):.2f})", color=col, lw=1.6)
    ax[1].plot(eq.index, eq / eq.cummax() - 1, color=col, lw=1.0)
ax[0].set_yscale("log"); ax[0].set_ylabel("growth of 1 (log)"); ax[0].legend(frameon=False); ax[0].grid(alpha=0.25)
ax[0].set_title("Crypto portfolio (C*, premium carry, cascade, ETH evening) on Binance perps, all at 15% volatility, 2022-01 to 2026-09 (descriptive)")
ax[1].set_ylabel("drawdown"); ax[1].grid(alpha=0.25)
fig.tight_layout(); fig.savefig(ROOT / "results/gen58_crypto_portfolio.png", dpi=130)

# ---------------- prop simulation on the hourly path
import gen55_firms as G55
FIRMS = {"FTMO 2-Step": "FTMO 2-Step $100k", "HyroTrader 2-Step": "HyroTrader Two-Step $100k", "HyroTrader 1-Step": "HyroTrader One-Step $100k",
         "CFT 1-Phase": "Crypto Fund Trader 1-Phase $100k", "FundedNext Stellar": "FundedNext Stellar 2-Step $100k",
         "BrightFunded Bright": "BrightFunded Two-Step Bright $100k"}
prop = []
for n in ("Portfolio (4 sleeves)", "C* alone"):
    h = series[n].loc["2022-01-01":"2026-09-30 23:00"]
    for sf in (0.4, 0.6):
        hc, hf = CS.to_daily(h), CS.to_daily(h * sf)
        for fn, key in FIRMS.items():
            f = PF.PRESETS[key]
            a = PF.attempts(hc, f, 1.0); p = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5)
            mi, avg_m = G55.months_with_income(hc, hf, f)
            prop.append({"portfolio": n, "firm": fn, "risk_funded": sf, "pass": a["P_pass"], "median_days_to_pass": a["median_days_to_pass"],
                         "net_2y": p["net_mean"], "net_2y_p10": p["net_p10"], "net_2y_p50": p["net_p50"], "p_profit": p["P_profit"],
                         "months_with_income": mi, "avg_month_m7_24": avg_m, "fees": p["fees"]})
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in prop[-1].items()}, flush=True)
pd.DataFrame(prop).to_csv(ROOT / "results/gen58_crypto_portfolio_prop.csv", index=False)

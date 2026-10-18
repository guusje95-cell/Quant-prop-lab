"""Gen78 CFD portfolio report: the crypto CFD book (C* + Weiss as CFDs, base costs) - statistics, monthly heatmap, equity curve,
prop results. Reads results/cache_gen74_hourly.parquet and results/gen74_prop.csv; writes results/gen78_cfd_portfolio.png and
results/gen78_cfd_stats.csv."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
H = pd.read_parquet(ROOT / "results/cache_gen74_hourly.parquet")
v5 = pd.read_parquet(ROOT / "results/cache_gen72_final.parquet")["portfolio"]


def daily15(h):
    d = h.groupby(h.index.floor("D")).sum().loc["2022-01-01":"2026-09-30"]
    return d * 0.15 / (d.std() * np.sqrt(365))


def stats(x, name):
    eq = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1; y = (1 + x).resample("YE").prod() - 1; dd = eq / eq.cummax() - 1
    neg = x[x < 0]; cagr = eq.iloc[-1] ** (365 / len(x)) - 1
    under = dd < 0; runs = (under != under.shift()).cumsum()
    return {"name": name, "Sharpe": x.mean() / x.std() * np.sqrt(365), "Sortino": x.mean() / np.sqrt((neg ** 2).sum() / len(x)) * np.sqrt(365),
            "CAGR": cagr, "MaxDD": dd.min(), "Calmar": cagr / abs(dd.min()), "Longest DD (days)": int(under.groupby(runs).sum().max()),
            "Positive months": (m > 0).mean(), "Worst month": m.min(), "Best month": m.max(), "Worst day": x.min(),
            **{str(d.year): v for d, v in y.items()}}


scen = {"CFD book, swap 3.3 bp/day (base)": daily15(H["swap 3.3 (base)"]), "CFD book, swap 6.6 bp/day": daily15(H["swap 6.6"]),
        "CFD book, 2x spread": daily15(H["swap 3.3, 2x spread"]), "Crypto-firm v5 (reference)": daily15(v5)}
ST = pd.DataFrame([stats(x, n) for n, x in scen.items()]); ST.to_csv(ROOT / "results/gen78_cfd_stats.csv", index=False)
pd.set_option("display.width", 250); print(ST.round(3).to_string())
B = scen["CFD book, swap 3.3 bp/day (base)"]
M = (1 + B).resample("ME").prod() - 1
heat = pd.DataFrame({"y": M.index.year, "m": M.index.month, "r": M.to_numpy()}).pivot(index="y", columns="m", values="r")
heat["Year"] = (1 + B).resample("YE").prod().to_numpy() - 1
heat.to_csv(ROOT / "results/gen78_cfd_monthly.csv"); print((heat * 100).round(1).to_string())

fig = plt.figure(figsize=(14, 12)); gs = fig.add_gridspec(3, 2, height_ratios=[1.3, 0.6, 1.1], hspace=0.35, wspace=0.18, top=0.94)
ax = fig.add_subplot(gs[0, :])
for n, x in scen.items():
    e = (1 + x).cumprod(); ax.plot(e.index, e, lw=2.2 if "base" in n else 1.0, label=f"{n}  Sharpe {x.mean() / x.std() * np.sqrt(365):.2f}",
                                   color={"CFD book, swap 3.3 bp/day (base)": "#0b5394", "CFD book, swap 6.6 bp/day": "#6fa8dc",
                                          "CFD book, 2x spread": "#9fc5e8", "Crypto-firm v5 (reference)": "#999999"}[n])
ax.set_yscale("log"); ax.legend(loc="upper left", fontsize=9); ax.grid(alpha=0.3)
ax.set_title("CFD-firm portfolio: C* + Weiss expiry traded as crypto CFDs (spread + swap, no funding), 15% vol, 2022-01..2026-09")
ax = fig.add_subplot(gs[1, :]); e = (1 + B).cumprod(); dd = e / e.cummax() - 1
ax.fill_between(dd.index, dd, 0, color="#cc0000", alpha=0.35); ax.set_title(f"Drawdown, base costs (max {dd.min():.1%})"); ax.grid(alpha=0.3)
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
ax = fig.add_subplot(gs[2, 0]); hv = heat.drop(columns="Year").to_numpy() * 100
ax.imshow(hv, cmap="RdYlGn", vmin=-8, vmax=8, aspect="auto"); ax.set_xticks(range(12)); ax.set_xticklabels(list("JFMAMJJASOND"))
ax.set_yticks(range(len(heat))); ax.set_yticklabels(heat.index)
for i in range(hv.shape[0]):
    for j in range(hv.shape[1]):
        if np.isfinite(hv[i, j]):
            ax.text(j, i, f"{hv[i, j]:.1f}", ha="center", va="center", fontsize=7.5)
ax.set_title("Monthly returns (%), base costs")
ax = fig.add_subplot(gs[2, 1]); yr = heat["Year"] * 100
ax.bar(yr.index.astype(str), yr, color=["#6aa84f" if v > 0 else "#cc0000" for v in yr])
for i, v in enumerate(yr):
    ax.text(i, v + (0.5 if v >= 0 else -1.5), f"{v:.1f}%", ha="center", fontsize=9)
ax.set_title("Calendar-year returns (2026 = Jan-Sep)"); ax.grid(alpha=0.3, axis="y")
fig.savefig(ROOT / "results/gen78_cfd_portfolio.png", dpi=110, bbox_inches="tight"); print("chart saved")

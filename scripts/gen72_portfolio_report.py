"""Gen72 portfolio construction (P0-P3, point-in-time) on the selected sleeves + Weiss W1 at half weight, then the full report:
statistics, monthly heatmap, equity curves, drawdown, rolling Sharpe, correlations and prop simulation.
Writes results/gen72_portfolio.csv, results/gen72_stats.csv, results/gen72_monthly.csv, results/gen72_prop.csv,
results/cache_gen72_final.parquet and results/gen72_*.png."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen55_firms as G55
from qpl.lab import propfirms as PF

warnings.filterwarnings("ignore")
END = "2026-09-30"
VOL = 0.15


def to_daily_stop(h, stop):
    """Daily net/worst/best from the hourly path; flat for the rest of the day once the loss reaches `stop` (exit 10 bp worse)."""
    rows = []
    for d, gg in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + gg.to_numpy())
        if stop > 0 and (p <= 1 - stop).any():
            k = int(np.argmax(p <= 1 - stop)); close = p[k] - 0.001
            rows.append((d, close - 1, min(p[:k + 1].min(), close) - 1, max(p[:k + 1].max(), 1.0) - 1))
        else:
            rows.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day")


def sharpe(x):
    x = x.fillna(0.0)
    return float(x.mean() / x.std() * np.sqrt(365)) if x.std() > 0 else np.nan


# ---------------------------------------------------------------- sleeves (hourly)
Hs = pd.read_parquet(ROOT / "results/cache_gen72_sleeves_hourly.parquet").loc[:END + " 23:00"]
w1d = pd.read_parquet(ROOT / "results/cache_gen70_daily.parquet")["W1 Weiss reversal, last Friday (PRIMARY)"]
w1h = pd.Series(0.0, index=Hs.index)
t = w1d[w1d != 0].index + pd.Timedelta(hours=9)                                # trade 08:00-10:00, booked in the 09:00 bar
w1h.loc[w1h.index.intersection(t)] = w1d[w1d != 0].reindex(t - pd.Timedelta(hours=9)).to_numpy()[: len(w1h.index.intersection(t))]
Hs["Weiss expiry"] = w1h
SLEEVES = list(Hs.columns)
D = Hs.groupby(Hs.index.floor("D")).sum()


def month_starts(idx):
    return idx[~idx.to_period("M").duplicated()]


def weights(method):
    """Sleeve weights per day, decided at the previous close, recomputed at each month start from the trailing 365 days."""
    W = pd.DataFrame(np.nan, index=D.index, columns=SLEEVES)
    for m in month_starts(D.index):
        hist = D.loc[m - pd.Timedelta(days=365):m - pd.Timedelta(days=1)]
        live = [c for c in SLEEVES if (hist[c] != 0).sum() >= 30 and hist[c].std() > 0]
        if len(live) < 2:
            continue
        if method == "P0":                                             # full-sample vols (the v4 recipe, look-ahead in the scale)
            sd = D.loc["2021-12-01":END, live].std()
            w = 0.10 / sd
        else:
            cov = hist[live].cov(); sd = np.sqrt(np.diag(cov)); w = pd.Series(0.10 / sd, index=live)
            if method == "P2":                                         # equal risk contribution
                S = cov.to_numpy(); x = np.ones(len(live)) / sd
                for _ in range(500):
                    rc = x * (S @ x); x = x * np.sqrt(rc.mean() / rc)
                w = pd.Series(x, index=live)
            elif method == "P3":                                       # long-only min variance, 50% shrinkage to diagonal
                from scipy.optimize import minimize
                S = 0.5 * cov.to_numpy() + 0.5 * np.diag(np.diag(cov.to_numpy())); n = len(live)
                r = minimize(lambda v: v @ S @ v, np.ones(n) / n, bounds=[(0, 1)] * n, constraints=({"type": "eq", "fun": lambda v: v.sum() - 1},))
                w = pd.Series(r.x, index=live) / np.sqrt(r.x @ S @ r.x)
        w = w / len(live)
        if "Weiss expiry" in w:
            w["Weiss expiry"] *= 0.5                                   # Gen70: half weight
        W.loc[m, w.index] = w.to_numpy(); W.loc[m, [c for c in SLEEVES if c not in w.index]] = 0.0
    return W.ffill().fillna(0.0)


def build(method):
    W = weights(method)
    Wh = W.reindex(Hs.index.floor("D")).set_axis(Hs.index)
    raw = (Hs * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (VOL / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1)            # point-in-time level
    x1 = rawd * lvl
    tgt = (VOL / (x1.rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1)                # 30d vol targeting, cap 1.5
    mult = (lvl * tgt).loc["2022-01-01":END]
    ph = (raw * mult.reindex(raw.index.floor("D")).set_axis(raw.index)).loc["2022-01-01":END + " 23:00"].dropna()
    pdl = ph.groupby(ph.index.floor("D")).sum()
    k = VOL / (pdl.std() * np.sqrt(365))                                                        # descriptive: realised vol to 15%
    return ph * k, W


# ---------------------------------------------------------------- method choice
rows, built = [], {}
for m in ("P0", "P1", "P2", "P3"):
    ph, W = build(m); built[m] = (ph, W); d = ph.groupby(ph.index.floor("D")).sum()
    eq = (1 + d).cumprod()
    rows.append({"method": m, "2022-24": sharpe(d.loc["2022":"2024"]), "HOLD 2025-26": sharpe(d.loc["2025":]), "2022-26": sharpe(d),
                 "maxDD": float((eq / eq.cummax() - 1).min()), "avg_weights": W.loc["2022":].mean().round(3).to_dict()})
    print(rows[-1], flush=True)
pt = pd.DataFrame(rows); pt.to_csv(ROOT / "results/gen72_portfolio.csv", index=False)
cand = pt[pt.method.isin(["P1", "P2", "P3"])].sort_values("2022-24", ascending=False).iloc[0]
p1_hold = float(pt.loc[pt.method == "P1", "HOLD 2025-26"].iloc[0])
CHOSEN = cand.method if cand["HOLD 2025-26"] >= p1_hold else "P1"
print("chosen method:", CHOSEN, flush=True)
PH, WCH = built[CHOSEN]
PD = PH.groupby(PH.index.floor("D")).sum()
pd.DataFrame({"portfolio": PH}).to_parquet(ROOT / "results/cache_gen72_final.parquet")

# reference portfolios for the comparison table
v4h = CS.portfolio_v3(cols=("C*", "premium carry", "cascade limit strict", "trend 4h"))
V4D = v4h.groupby(v4h.index.floor("D")).sum()


# ---------------------------------------------------------------- statistics
def stats(x, name):
    x = x.loc["2022-01-01":END].fillna(0.0); eq = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1; y = (1 + x).resample("YE").prod() - 1
    neg = x[x < 0]; cagr = eq.iloc[-1] ** (365 / len(x)) - 1; dd = (eq / eq.cummax() - 1)
    # longest drawdown in days
    under = dd < 0; runs = (under != under.shift()).cumsum(); longest = int(under.groupby(runs).sum().max())
    return {"name": name, "CAGR": cagr, "Vol": x.std() * np.sqrt(365), "Sharpe": sharpe(x),
            "Sortino": x.mean() / np.sqrt((neg ** 2).sum() / len(x)) * np.sqrt(365), "MaxDD": dd.min(), "Calmar": cagr / abs(dd.min()),
            "Longest DD (days)": longest, "Positive months": (m > 0).mean(), "Best month": m.max(), "Worst month": m.min(),
            "Worst day": x.min(), "Best day": x.max(), "Skew (daily)": x.skew(),
            **{f"{d.year}": v for d, v in y.items()}}


def at_vol(x, v=VOL):
    x = x.loc["2022-01-01":END].fillna(0.0); return x * v / (x.std() * np.sqrt(365))


ST = [stats(PD, f"FINAL portfolio ({CHOSEN})"), stats(V4D, "v4 (previous best)")]
for c in SLEEVES:
    ST.append(stats(at_vol(D[c]), f"sleeve: {c} (at 15% vol)"))
st = pd.DataFrame(ST); st.to_csv(ROOT / "results/gen72_stats.csv", index=False)
pd.set_option("display.width", 300); print(st.round(3).to_string(), flush=True)

M = (1 + PD).resample("ME").prod() - 1
heat = pd.DataFrame({"year": M.index.year, "month": M.index.month, "ret": M.to_numpy()}).pivot(index="year", columns="month", values="ret")
heat["Year"] = (1 + PD).resample("YE").prod().to_numpy() - 1
heat.to_csv(ROOT / "results/gen72_monthly.csv")
corr = D.loc["2022":END].corr()

# ---------------------------------------------------------------- charts
plt.rcParams.update({"font.size": 10})
fig = plt.figure(figsize=(14, 17))
gs = fig.add_gridspec(4, 2, height_ratios=[1.3, 0.7, 1.1, 1.0], hspace=0.35, wspace=0.18)
ax = fig.add_subplot(gs[0, :])
eqf = (1 + PD).cumprod(); eqv = (1 + V4D.loc["2022":]).cumprod()
ax.plot(eqf.index, eqf, lw=2.4, color="#0b5394", label=f"Final portfolio  Sharpe {sharpe(PD):.2f}")
ax.plot(eqv.index, eqv, lw=1.2, color="#999999", label=f"v4 (previous)  Sharpe {sharpe(V4D.loc['2022':]):.2f}")
cols = {"C*": "#e69138", "premium carry": "#6aa84f", "cascade limit strict": "#cc0000", "trend 4h": "#674ea7", "Weiss expiry": "#45818e"}
for c in SLEEVES:
    e = (1 + at_vol(D[c])).cumprod(); ax.plot(e.index, e, lw=0.8, alpha=0.75, color=cols.get(c), label=f"{c} (15% vol)  {sharpe(D[c].loc['2022':]):.2f}")
ax.set_yscale("log"); ax.set_title("Equity curve, 2022-01 to 2026-09 (all at 15% annual vol, net of costs and funding)"); ax.legend(loc="upper left", fontsize=8.5, ncol=2); ax.grid(alpha=0.3)
ax = fig.add_subplot(gs[1, :])
dd = eqf / eqf.cummax() - 1; ax.fill_between(dd.index, dd, 0, color="#cc0000", alpha=0.35)
ax.set_title(f"Drawdown of the final portfolio (max {dd.min():.1%})"); ax.grid(alpha=0.3)
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
ax = fig.add_subplot(gs[2, 0])
hv = heat.drop(columns="Year").to_numpy() * 100
im = ax.imshow(hv, cmap="RdYlGn", vmin=-8, vmax=8, aspect="auto")
ax.set_xticks(range(12)); ax.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]); ax.set_yticks(range(len(heat))); ax.set_yticklabels(heat.index)
for i in range(hv.shape[0]):
    for j in range(hv.shape[1]):
        if np.isfinite(hv[i, j]):
            ax.text(j, i, f"{hv[i, j]:.1f}", ha="center", va="center", fontsize=7.5)
ax.set_title("Monthly returns (%), final portfolio")
ax = fig.add_subplot(gs[2, 1])
yr = heat["Year"] * 100; ax.bar(yr.index.astype(str), yr, color=["#6aa84f" if v > 0 else "#cc0000" for v in yr])
for i, v in enumerate(yr):
    ax.text(i, v + (0.5 if v >= 0 else -1.5), f"{v:.1f}%", ha="center", fontsize=9)
ax.set_title("Calendar-year returns (2026 = Jan-Sep)"); ax.grid(alpha=0.3, axis="y")
ax = fig.add_subplot(gs[3, 0])
rs = PD.rolling(365).mean() / PD.rolling(365).std() * np.sqrt(365); ax.plot(rs.index, rs, color="#0b5394"); ax.axhline(0, color="k", lw=0.6)
ax.set_title("Rolling 1-year Sharpe, final portfolio"); ax.grid(alpha=0.3)
ax = fig.add_subplot(gs[3, 1])
im2 = ax.imshow(corr.to_numpy(), cmap="coolwarm", vmin=-1, vmax=1)
ax.set_xticks(range(len(corr))); ax.set_xticklabels([c.replace(" limit strict", "") for c in corr.columns], rotation=30, ha="right", fontsize=8)
ax.set_yticks(range(len(corr))); ax.set_yticklabels([c.replace(" limit strict", "") for c in corr.columns], fontsize=8)
for i in range(len(corr)):
    for j in range(len(corr)):
        ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
ax.set_title("Sleeve correlations (daily, 2022-26)")
fig.suptitle("Crypto prop portfolio (Gen72 final): C* + premium carry + cascade + 4h trend + Weiss expiry", fontsize=13, y=0.995)
fig.savefig(ROOT / "results/gen72_report.png", dpi=110, bbox_inches="tight")
print("chart saved", flush=True)

# ---------------------------------------------------------------- prop simulation (bootstrap, S50 daily stop, $100k, 2 years)
PROP = []
for key in ("HyroTrader One-Step $100k", "HyroTrader Two-Step $100k", "SizeProp One-Step $100k", "Crypto Fund Trader 1-Phase $100k"):
    f = PF.PRESETS[key]
    for sc, sf in ((0.75, 0.4), (1.0, 0.6), (1.25, 0.8)):
        hc = to_daily_stop(PH * sc, 0.5 * f.daily_loss); hf = to_daily_stop(PH * sf, 0.5 * f.daily_loss)
        a = PF.attempts(hc, f, 1.0)
        pb = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
        mi, am = G55.months_with_income(hc, hf, f)
        PROP.append({"firm": f.name, "risk_challenge": sc, "risk_funded": sf, "pass": a["P_pass"], "days_to_pass": a["median_days_to_pass"],
                     "boot_net": pb["net_mean"], "boot_p10": pb["net_p10"], "boot_p50": pb["net_p50"], "boot_p_profit": pb["P_profit"],
                     "months_with_income": mi, "avg_month": am})
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in PROP[-1].items()}, flush=True)
pd.DataFrame(PROP).to_csv(ROOT / "results/gen72_prop.csv", index=False)
print("done", flush=True)

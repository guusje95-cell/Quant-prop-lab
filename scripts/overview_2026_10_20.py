"""Overview 2026-10-20: the three validated books (crypto v7 on HyroTrader, CFD bf+P6 on BrightFunded, futures book on a
swing-friendly futures firm), with v6 / bf as reference. Equity curves, yearly/monthly stats, prop-firm payout simulation
(2 years, block bootstrap 500 paths, re-buy budget 5). Writes results/overview_2026_10_20/*."""
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "results/overview_2026_10_20"; OUT.mkdir(parents=True, exist_ok=True)
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
g = {"__file__": str(ROOT / "scripts/gen127_p6.py")}
s = open(ROOT / "scripts/gen127_p6.py").read(); exec(s.split("out = {")[0], g)
CS = g["CS"]
gg = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}
exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], gg)
H6 = gg["H6"]
P = pd.read_parquet(ROOT / "results/gen108_preds.parquet"); wml = P.pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
ml = CS._from_daily_weights(wml, ["BTC", "ETH"], 5).loc[:"2026-09-30 23:00"]
hourly = {"crypto v7 (HyroTrader)": CS.portfolio_v5(pd.concat([H6, ml.rename("ridge ML")], axis=1).fillna(0.0))[0],
          "crypto v6 (reference)": CS.portfolio_v5(H6)[0],
          "CFD bf + indices (BrightFunded)": g["vb"], "CFD bf (reference)": g["bb0"]}
fut = pd.read_parquet(ROOT / "results/gen143_book.parquet")["book"]
VOL = 0.15
daily, scaled_h = {}, {}
for k, h in hourly.items():
    h = h.loc["2022-01-01":"2026-09-30 23:00"]; d = h.groupby(h.index.floor("D")).sum(); f = VOL / (d.std() * np.sqrt(365))
    daily[k] = d * f; scaled_h[k] = h * f
fd = fut.loc["2022-01-01":"2026-09-30"]; ff = VOL / (fd.std() * np.sqrt(252)); daily["futures book (swing futures firm)"] = fd * ff


def stats(x, ann):
    eq = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1; y = (1 + x).resample("YE").prod() - 1
    return {"Sharpe": round(float(x.mean() / x.std() * np.sqrt(ann)), 2), "CAGR": round(float(eq.iloc[-1] ** (ann / len(x)) - 1), 3),
            "MaxDD": round(float((eq / eq.cummax() - 1).min()), 3), "positive months": round(float((m > 0).mean()), 2),
            "worst month": round(float(m.min()), 3), "best month": round(float(m.max()), 3), **{str(k.year): round(float(v), 3) for k, v in y.items()}}


ST = {k: stats(v, 252 if k.startswith("futures") else 365) for k, v in daily.items()}
pd.DataFrame(ST).T.to_csv(OUT / "stats.csv")
monthly = pd.DataFrame({k: (1 + v).resample("ME").prod() - 1 for k, v in daily.items()}); monthly.to_csv(OUT / "monthly.csv")
pd.DataFrame({k: (1 + v).cumprod() for k, v in daily.items()}).to_csv(OUT / "equity.csv")
# ---- prop simulations
FUT_FIRM = PF.Firm("Swing futures firm 50k (MFFU/Tradeify-like, ASSUMED)", 50_000, 150, (0.06,), 0.0, "initial", True, 0.04, "trailing_lock", False,
                   2, 0, 0.90, 14, 0.0, False, 0.0, "ASSUMED: $3,000 target, $2,000 end-of-day trailing that locks at the start balance, no daily limit, "
                   "overnight allowed, 90% split, payouts every 14 days, $150 fee. Verify on the firm's site.", payout_min=250)
JOBS = [("crypto v7 (HyroTrader)", "HyroTrader Two-Step $100k", 1.5, 1.0, 0.5), ("crypto v7 (HyroTrader)", "HyroTrader One-Step $100k", 1.25, 1.0, 0.6),
        ("crypto v6 (reference)", "HyroTrader Two-Step $100k", 1.5, 1.0, 0.5),
        ("CFD bf + indices (BrightFunded)", "BrightFunded Two-Step Classic $100k", 1.5, 1.0, 0.6), ("CFD bf (reference)", "BrightFunded Two-Step Classic $100k", 1.5, 1.0, 0.6)]
rows = []
for book, firm, sc, sf, st in JOBS:
    f = PF.PRESETS[firm]
    if firm.startswith("BrightFunded"):
        f = replace(f, fee=591.0, note=f.note + "; swap-free add-on fee 591")
    hh = scaled_h[book]; hc = to_daily_stop(hh * sc, st * f.daily_loss); hf = to_daily_stop(hh * sf, st * f.daily_loss)
    a = PF.attempts(hc, f, 1.0)
    pb = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    rows.append({"book": book, "firm": firm, "risk challenge/funded": f"{sc}/{sf}", "daily stop": st, "P(pass per attempt)": round(a["P_pass"], 2),
                 "fees paid": round(pb["fees"]), "payouts received": round(pb["paid"]), "net 2y mean": round(pb["net_mean"]), "net 2y p10": round(pb["net_p10"]),
                 "net 2y median": round(pb["net_p50"]), "P(profit)": round(pb["P_profit"], 2), "net per month": round(pb["net_per_month"]),
                 "days to funded (median)": pb["days_to_funded_median"], "days to 1st payout (median)": pb["days_to_first_payout_median"]})
    pb["curve"].to_csv(OUT / f"prop_curve_{book.split()[0]}_{firm.split()[0]}_{sc}.csv"); print(rows[-1], flush=True)
x = daily["futures book (swing futures firm)"]
dfut = pd.DataFrame({"net": x, "worst": x.clip(upper=0) * 1.3, "best": x.clip(lower=0)})       # intraday swings approximated (no intraday data)
for sc in (0.33, 0.5, 0.75):
    a = PF.attempts(dfut, FUT_FIRM, sc)
    pb = PF.pipeline(dfut, FUT_FIRM, 5, 1, sc, sc, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    rows.append({"book": "futures book (swing futures firm)", "firm": FUT_FIRM.name, "risk challenge/funded": f"{sc}/{sc} (x15% vol)", "daily stop": 0,
                 "P(pass per attempt)": round(a["P_pass"], 2), "fees paid": round(pb["fees"]), "payouts received": round(pb["paid"]),
                 "net 2y mean": round(pb["net_mean"]), "net 2y p10": round(pb["net_p10"]), "net 2y median": round(pb["net_p50"]), "P(profit)": round(pb["P_profit"], 2),
                 "net per month": round(pb["net_per_month"]), "days to funded (median)": pb["days_to_funded_median"], "days to 1st payout (median)": pb["days_to_first_payout_median"]})
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(OUT / "prop.csv", index=False)
# ---- chart
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(2, 1, figsize=(11, 8), gridspec_kw={"height_ratios": [3, 2]})
cols = {"crypto v7 (HyroTrader)": "#1f77b4", "crypto v6 (reference)": "#9ecae1", "CFD bf + indices (BrightFunded)": "#d62728", "CFD bf (reference)": "#fcae91",
        "futures book (swing futures firm)": "#2ca02c"}
for k, v in daily.items():
    ax[0].plot((1 + v).cumprod(), label=f"{k}  Sharpe {ST[k]['Sharpe']}", color=cols[k], lw=2 if "reference" not in k else 1, ls="-" if "reference" not in k else "--")
ax[0].set_yscale("log"); ax[0].set_title("Equity at 15% annual volatility, 2022-01 .. 2026-09 (backtest, net of costs)"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
m = monthly[["crypto v7 (HyroTrader)", "CFD bf + indices (BrightFunded)", "futures book (swing futures firm)"]]
w = 9; xs = np.arange(len(m))
for i, k in enumerate(m.columns):
    ax[1].bar(xs + (i - 1) * 0.28, m[k].to_numpy() * 100, width=0.28, color=cols[k], label=k)
ax[1].set_xticks(xs[::6]); ax[1].set_xticklabels([d.strftime("%Y-%m") for d in m.index[::6]], fontsize=7); ax[1].set_ylabel("% per month"); ax[1].axhline(0, color="k", lw=.5)
ax[1].set_title("Monthly returns at 15% vol"); ax[1].grid(alpha=.3, axis="y")
plt.tight_layout(); plt.savefig(OUT / "equity_curves.png", dpi=130)
print(json.dumps(ST, indent=1))

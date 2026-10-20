"""Overview v2 (after Gen212): current books, 2022-01..2026-09 at 15% vol, stats + equity chart. Writes results/overview_v2/."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "results/overview_v2"; OUT.mkdir(parents=True, exist_ok=True)
g = {"__file__": str(ROOT / "scripts/gen171_crypto_calendar.py")}; exec(open(ROOT / "scripts/gen171_crypto_calendar.py").read().split("\ndays = pd.date_range")[0], g)
v7 = g["v7"]
k = {"__file__": str(ROOT / "scripts/gen168_bf_merged.py")}; exec(open(ROOT / "scripts/gen168_bf_merged.py").read().split("\nP6 = p6()")[0], k)
bf = k["CS"].portfolio_v5(pd.concat([k["HB0"], (k["p6"]() + k["r1"](1e-4)).rename("vol-managed indices")], axis=1).fillna(0.0))[0]
daily = {}
for n, h in (("crypto v7 (HyroTrader)", v7), ("CFD bf + index sleeve (BrightFunded)", bf)):
    d = h.loc["2022-01-01":"2026-09-30 23:00"]; d = d.groupby(d.index.floor("D")).sum(); daily[n] = (d, 365)
for n, f in (("futures book (swing futures firm)", "gen205_book"), ("index-CFD book (2nd CFD account)", "gen201_book")):
    d = pd.read_parquet(ROOT / f"results/{f}.parquet")["book"].loc["2022-01-01":"2026-09-30"]; daily[n] = (d, 252)
ST = {}
for n, (d, ann) in daily.items():
    x = d * 0.15 / (d.std() * np.sqrt(ann)); eq = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1; y = (1 + x).resample("YE").prod() - 1
    sh = lambda a, b: round(float(x.loc[a:b].mean() / x.loc[a:b].std() * np.sqrt(ann)), 2)
    ST[n] = {"Sharpe 2022-26": sh("2022", "2026-09-30"), "Sharpe 2023-26": sh("2023", "2026-09-30"), "CAGR @15%vol": round(float(eq.iloc[-1] ** (ann / len(x)) - 1), 3),
             "MaxDD": round(float((eq / eq.cummax() - 1).min()), 3), "positive months": round(float((m > 0).mean()), 2), "worst month": round(float(m.min()), 3),
             **{str(i.year): round(float(v), 3) for i, v in y.items()}}
    daily[n] = x
pd.DataFrame(ST).T.to_csv(OUT / "stats.csv"); json.dump(ST, open(OUT / "stats.json", "w"), indent=1)
C = pd.DataFrame({n: v.resample("D").sum() for n, v in daily.items()}).loc["2023":].fillna(0.0); C = C[C.index.weekday < 5]
print(json.dumps(ST, indent=1)); print(C.corr().round(2))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(11, 6))
for n, x in daily.items():
    ax.plot((1 + x).cumprod(), label=f"{n}  Sharpe 22-26 {ST[n]['Sharpe 2022-26']} / 23-26 {ST[n]['Sharpe 2023-26']}", lw=1.8)
ax.set_yscale("log"); ax.grid(alpha=.3); ax.legend(fontsize=8); ax.set_title("Current books at 15% annual volatility, 2022-01 .. 2026-09 (backtest, net of costs)")
plt.tight_layout(); plt.savefig(OUT / "equity_curves.png", dpi=130)

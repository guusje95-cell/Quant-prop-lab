"""Full overview (2026-10-19): v5, v6 (crypto firms, Binance perps), FundedNext CFD book (swap-free, 9 coins, 1:1, 4 bp) and the BrightFunded
CFD book (paper 'bf': swap-free, 1:5, 1.2 bp). Daily series at 15% vol 2022-01..2026-09, stats, monthly table, prop results.
Writes results/overview_2026_10.json and results/overview_2026_10_series.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; S = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
H5 = CS.v5_sleeves(); H6 = pd.concat([H5, CS.delev_bounce().rename("delev bounce")], axis=1).fillna(0.0)
series = {"v5 (crypto firm)": CS.portfolio_v5(H5)[0], "v6 (crypto firm)": CS.portfolio_v5(H6)[0],
          "BrightFunded CFD book": pd.read_parquet(ROOT / "results/cache_bf_final.parquet")["portfolio"]}
g = {"__file__": str(ROOT / "scripts/gen103_fundednext.py")}; sys.argv = [sys.argv[0], str(S)]
exec(open(ROOT / "scripts/gen103_fundednext.py").read().split("rows, P = [], []")[0], g)
FN = g["FN"]; hf, _ = g["hourly"](g["BOOK6"], 1.0, 1.0, spread=(5, 10), comm=4.0, swap=0.0, universe=FN, weekend_flat=False)
series["FundedNext CFD book"] = hf
D = {}
for k, h in series.items():
    d = h.groupby(h.index.floor("D")).sum().loc["2022-01-01":"2026-09-30"]; D[k] = d * 0.15 / (d.std() * np.sqrt(365))
D = pd.DataFrame(D).fillna(0.0); D.to_parquet(ROOT / "results/overview_2026_10_series.parquet")
stats = {}
for k in D:
    x = D[k]; eq = (1 + x).cumprod(); dd = eq / eq.cummax() - 1; m = (1 + x).resample("ME").prod() - 1; y = (1 + x).resample("YE").prod() - 1
    neg = x[x < 0]; under = (dd < 0).astype(int); runs = under.groupby((under == 0).cumsum()).sum()
    stats[k] = {"Sharpe": x.mean() / x.std() * np.sqrt(365), "Sortino": x.mean() / neg.std() * np.sqrt(365), "CAGR": eq.iloc[-1] ** (365 / len(x)) - 1,
                "MaxDD": dd.min(), "Calmar": (eq.iloc[-1] ** (365 / len(x)) - 1) / -dd.min(), "pos_months": (m > 0).mean(), "best_month": m.max(),
                "worst_month": m.min(), "worst_day": x.min(), "longest_dd_days": int(runs.max()),
                "TEST_2023_24": x.loc["2023":"2024"].mean() / x.loc["2023":"2024"].std() * np.sqrt(365),
                "HOLD_2025_26": x.loc["2025":].mean() / x.loc["2025":].std() * np.sqrt(365),
                "years": {str(k2.year): v for k2, v in y.items()}, "months": {k2.strftime("%Y-%m"): v for k2, v in m.items()}}
    print(k, {a: round(b, 3) for a, b in stats[k].items() if isinstance(b, float)}, flush=True)
weekly = D.resample("W").sum()
eqs = {k: (1 + D[k]).cumprod().resample("W").last() for k in D}
dds = {k: ((1 + D[k]).cumprod() / (1 + D[k]).cumprod().cummax() - 1).resample("W").min() for k in D}
prop = []
v6p = pd.read_csv(ROOT / "results/gen90_v6_prop.csv")
for r in v6p.itertuples():
    prop.append({"book": "v6 (crypto firm)" if r.book.startswith("v6") else "v5 (crypto firm)", "firm": r.firm, "fee": 749 if "One" in r.firm else 579,
                 "setting": r.setting, "pass": r._4, "mean_net": r.mean_net, "p10": r.p10, "P_profit": r.P_profit})
fnp = pd.read_csv(ROOT / "results/gen103_prop.csv")
r = fnp[fnp.book.str.startswith("6-sleeve")].iloc[0]
prop.append({"book": "FundedNext CFD book", "firm": "FundedNext Stellar 2-Step $100k swap-free", "fee": 605, "setting": "1.5/1.0/0.6, 1:1",
             "pass": r["pass"], "mean_net": r["mean_net"], "p10": r["p10"], "P_profit": r["P_profit"]})
json.dump({"stats": stats, "equity_weekly": {k: {"t": [str(i.date()) for i in v.index], "v": v.round(5).tolist()} for k, v in eqs.items()},
           "dd_weekly": {k: v.round(5).tolist() for k, v in dds.items()}, "prop": prop}, open(ROOT / "results/overview_2026_10.json", "w"), default=float)
print("done")

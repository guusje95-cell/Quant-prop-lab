"""Gen62 H7 + crypto-prop sizing (descriptive): 3-sleeve crypto portfolio (C*, premium carry, cascade) with equal risk vs monthly
inverse-vol weights; prop outcomes at three risk levels on the hourly path 2022-01..2026-09. Writes results/gen62_portfolio.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen55_firms as G55
from qpl.lab import propfirms as PF

H = CS.all_sleeves()[["C*", "premium carry", "cascade"]].loc["2021-12-01":]
D = H.groupby(H.index.floor("D")).sum()
base = {c: 0.10 / (D[c].std() * np.sqrt(365)) for c in D}
eq_h = H.mul(pd.Series(base)).mean(axis=1)
vol90 = D.rolling(90).std().shift(1) * np.sqrt(365)                      # trailing, known in advance
wm = (0.10 / vol90).resample("MS").first().reindex(D.index).ffill()
wm = wm.div(wm.sum(axis=1), axis=0) * 3                                   # same total weight as equal risk
iv_h = (H * wm.reindex(H.index.floor("D")).set_axis(H.index)).mean(axis=1)


def stats(h):
    x = h.groupby(h.index.floor("D")).sum().loc["2022":]
    x = x * 0.15 / (x.std() * np.sqrt(365))
    m = (1 + x).resample("ME").prod() - 1; eq = (1 + x).cumprod()
    return {"Sharpe": x.mean() / x.std() * np.sqrt(365), "Positive months": (m > 0).mean(), "Max DD": (eq / eq.cummax() - 1).min(),
            "Worst month": m.min(), "2022": (1 + x.loc["2022"]).prod() - 1, "2023+ Sharpe": x.loc["2023":].mean() / x.loc["2023":].std() * np.sqrt(365)}


print("equal risk:", {k: round(v, 3) for k, v in stats(eq_h).items()})
print("inverse-vol monthly:", {k: round(v, 3) for k, v in stats(iv_h).items()})

port = eq_h.loc["2022-01-01":"2026-09-30 23:00"]
k = 0.15 / (port.groupby(port.index.floor("D")).sum().std() * np.sqrt(365)); port = port * k
FIRMS = {"HyroTrader 1-Step": "HyroTrader One-Step $100k", "HyroTrader 2-Step": "HyroTrader Two-Step $100k", "CFT 1-Phase": "Crypto Fund Trader 1-Phase $100k",
         "SizeProp 1-Step": "SizeProp One-Step $100k", "Breakout Classic": "Breakout One-Step Classic $100k"}
rows = []
for sc, sf in ((0.75, 0.4), (1.0, 0.4), (1.0, 0.6), (1.25, 0.5), (1.5, 0.6)):
    hc, hf = CS.to_daily(port * sc), CS.to_daily(port * sf)
    for fn, key in FIRMS.items():
        f = PF.PRESETS[key]
        a = PF.attempts(hc, f, 1.0); p = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5)
        mi, am = G55.months_with_income(hc, hf, f)
        rows.append({"firm": fn, "risk_challenge": sc, "risk_funded": sf, "pass": a["P_pass"], "fail_daily": a["P_fail_daily"], "days_to_pass": a["median_days_to_pass"],
                     "net_2y": p["net_mean"], "net_2y_p10": p["net_p10"], "p_profit": p["P_profit"], "months_with_income": mi, "avg_month": am})
out = pd.DataFrame(rows); out.to_csv(ROOT / "results/gen62_portfolio.csv", index=False)
pd.set_option("display.width", 250); print(out.round(3).to_string())

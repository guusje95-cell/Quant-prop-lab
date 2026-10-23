"""Gen328 parts 1 and 3 (config/gen328_protocol.json): sleeve decay, crash stress and emergency brakes for v8.6 and bf2.6.
Writes results/gen328.json (part 2 in scripts/gen328_caps.py)."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import bf2lab as F
from qpl.lab import binance_pack as B
END = L.END; ROOT = L.ROOT
out = {}
SL = {"v8.6": pd.concat([L.H6, L.RIDGE] + L.ALTK, axis=1).fillna(0.0),
      "bf2.6": pd.concat([F.HB0, F.IS0, F.HB_RIDGE.rename("ridge ML")] + F.ALTK_BF, axis=1).fillna(0.0)}

# ---- part 1: sleeve decay --------------------------------------------------------------------------------------------
for bk, H in SL.items():
    D = H.groupby(H.index.floor("D")).sum().loc["2020-01-01":END]; rows = {}
    for s in D.columns:
        x = D[s]; x = x.loc[x.ne(0).idxmax():]
        r12 = x.rolling(365, min_periods=300).apply(lambda z: z.mean() / z.std() * np.sqrt(365) if z.std() > 0 else np.nan, raw=True).dropna()
        r6 = x.rolling(182, min_periods=150).apply(lambda z: z.mean() / z.std() * np.sqrt(365) if z.std() > 0 else np.nan, raw=True).dropna()
        last = float(r12.iloc[-1]) if len(r12) else np.nan
        rows[s] = {"since": str(x.index[0].date()), "full Sharpe": round(float(x.mean() / x.std() * np.sqrt(365)), 2),
                   "last 12 m": round(last, 2), "last 6 m": round(float(r6.iloc[-1]), 2) if len(r6) else None,
                   "percentile of last 12 m in its history": round(float((r12 < last).mean()), 2) if len(r12) else None,
                   "share of 12-m windows < 0": round(float((r12 < 0).mean()), 2) if len(r12) else None,
                   "10th pct of 12-m Sharpe": round(float(r12.quantile(0.1)), 2) if len(r12) else None,
                   "WARNING (12 m < 0 and < own p10)": bool(len(r12) and last < 0 and last < r12.quantile(0.1))}
    out[f"1 sleeve decay {bk}"] = rows
    print(bk); print(pd.DataFrame(rows).T.to_string(), flush=True)

# ---- part 3: crash stress and brakes ----------------------------------------------------------------------------------
btc = B.k5("BTC").close.resample("1D").last().pct_change()
bsd = btc.rolling(30).std()
EVENTS = {"Luna 2022-05-09..12": ("2022-05-09", "2022-05-12"), "3AC / Celsius 2022-06-13..18": ("2022-06-13", "2022-06-18"),
          "FTX 2022-11-08..10": ("2022-11-08", "2022-11-10"), "yen-carry unwind 2024-08-05": ("2024-08-05", "2024-08-05"),
          "liquidation crash 2025-10-10..11": ("2025-10-10", "2025-10-11")}


def stats(h):
    d = h.groupby(h.index.floor("D")).sum().loc["2022-01-01":END]; eq = (1 + d).cumprod(); dd = float((eq / eq.cummax() - 1).min())
    s = lambda a, z: round(float(d.loc[a:z].mean() / d.loc[a:z].std() * np.sqrt(365)), 3)
    stops = breaches = 0
    for _, g in h.loc["2022-01-01":].groupby(h.loc["2022-01-01":].index.floor("D")):
        c = g.cumsum(); hit = c[c <= -0.025]
        if len(hit):
            stops += 1; breaches += int(c.loc[hit.index[0]] <= -0.05)
    return {"sharpe D/T/H": [s("2022-01-01", END), s("2022", "2022"), s("2023", "2024"), s("2025", END)], "worst day %": round(float(d.min()) * 100, 2),
            "max drawdown %": round(dd * 100, 1), "2.5% stop days": stops, "breach days (hour jumped past 5%)": breaches}


for bk, f in (("v8.6", "v86"), ("bf2.6", "bf26")):
    h = pd.read_parquet(ROOT / f"results/cache_{f}_final.parquet")["portfolio"] * 2.0          # paper risk 2.0
    d = h.groupby(h.index.floor("D")).sum()
    worst = d.nsmallest(10)
    out[f"3 worst 10 days {bk} (risk 2.0)"] = [{"day": str(k.date()), "book %": round(float(v) * 100, 2), "BTC %": round(float(btc.get(k, np.nan)) * 100, 1)} for k, v in worst.items()]
    out[f"3 named events {bk}"] = {nm: {"book %": round(float(d.loc[a:z].sum()) * 100, 2), "worst day %": round(float(d.loc[a:z].min()) * 100, 2),
                                        "BTC %": round(float(((1 + btc.loc[a:z]).prod() - 1) * 100), 1)} for nm, (a, z) in EVENTS.items()}
    # brakes: factor for day t decided from information up to the end of day t-1
    stopday = pd.Series(False, index=d.index)
    for k, g in h.groupby(h.index.floor("D")):
        stopday[k] = bool((g.cumsum() <= -0.025).any())
    b1 = pd.Series(1.0, index=d.index); s1 = stopday.shift(1, fill_value=False) | stopday.shift(2, fill_value=False); b1[s1] = 0.5
    big = (btc.abs() > 3 * bsd.shift(1)).reindex(d.index).fillna(False)
    b2 = pd.Series(1.0, index=d.index); b2[big.shift(1, fill_value=False)] = 0.5
    base = stats(h); out[f"3 brakes {bk}"] = {"none": base}
    for nm, fac in (("B1 half risk 2 days after a stop day", b1), ("B2 half risk after a 3-sd BTC day", b2)):
        hb = h * fac.reindex(h.index.floor("D")).set_axis(h.index).fillna(1.0); st = stats(hb)
        st["adopt (Sharpe >= base - 0.05, worst day and max DD better)"] = bool(st["sharpe D/T/H"][0] >= base["sharpe D/T/H"][0] - 0.05
                                                                               and st["worst day %"] > base["worst day %"] and st["max drawdown %"] > base["max drawdown %"])
        st["days at half risk"] = int((fac < 1).loc["2022":].sum()); out[f"3 brakes {bk}"][nm] = st
    print(bk, json.dumps(out[f"3 named events {bk}"]), json.dumps(out[f"3 brakes {bk}"]), flush=True)
json.dump(out, open(ROOT / "results/gen328.json", "w"), indent=1, default=str)

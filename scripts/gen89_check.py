"""Gen89 robustness checks for H4 deleveraging bounce (descriptive; no selection): neighbours, per coin, 2x costs, event count,
top-event removal, 1-hour-later entry. Writes results/gen89_check.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen89_cfd.py")}
exec(open(ROOT / "scripts/gen89_cfd.py").read().split("C85 = pd.read_parquet")[0], g)
B, CFD, fhp, d2h, dsh, IDX = g["B"], g["CFD"], g["fhp"], g["d2h"], g["dsh"], g["IDX"]


def sig_w(th, hold=2, coins=("BTC", "ETH"), lag_h=0):
    w = pd.DataFrame(0.0, index=pd.date_range("2020-01-01", "2026-09-30"), columns=CFD); ev = 0
    for c in coins:
        m = B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1h").last().ffill(); px = B.k5(c).close.resample("1h").last()
        mid = pd.date_range("2021-12-02", "2026-09-30"); t = mid - pd.Timedelta(minutes=5)
        f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
        sig = pd.Series((f(m, t) / f(m, t - pd.Timedelta(days=1)) - 1 < -th) & (f(px, t) < f(px, t - pd.Timedelta(days=1))), index=mid - pd.Timedelta(days=1))
        ev += int(sig.sum())
        w.loc[sig.index, c] = (sig.astype(float).rolling(hold, min_periods=1).max() * 0.5).to_numpy()
    return w, ev


def run(th=0.10, hold=2, coins=("BTC", "ETH"), mult=1.0, lag_h=0):
    w, ev = sig_w(th, hold, coins)
    pos = d2h(w)
    if lag_h:
        pos = pos.shift(lag_h).fillna(0.0)
    if mult != 1.0:
        g["ns"]["SPREAD"].update({k: v * mult for k, v in g["ns"]["SPREAD"].items()})
    h = fhp(pos, 3.3)
    if mult != 1.0:
        g["ns"]["SPREAD"].update({k: v / mult for k, v in g["ns"]["SPREAD"].items()})
    return h.reindex(IDX).fillna(0.0), ev


rows = []
for nm, kw in (("base 10% hold 2", {}), ("th 7.5%", {"th": 0.075}), ("th 12.5%", {"th": 0.125}), ("th 15%", {"th": 0.15}),
               ("hold 1", {"hold": 1}), ("hold 3", {"hold": 3}), ("hold 5", {"hold": 5}), ("BTC only", {"coins": ("BTC",)}),
               ("ETH only", {"coins": ("ETH",)}), ("entry 1h later", {"lag_h": 1}), ("entry 4h later", {"lag_h": 4})):
    h, ev = run(**kw)
    rows.append({"variant": nm, "signals": ev, "DEV 2022": dsh(h, "2022", "2022-12-31"), "TEST": dsh(h, "2023", "2024-12-31"),
                 "HOLD": dsh(h, "2025", "2026-09-30"), "2022-26": dsh(h, "2022", "2026-09-30")})
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
# 2x spread: rebuild with doubled costs via positions
w, ev = sig_w(0.10); pos = d2h(w)
R = g["R1h"]; turn = pos.diff().abs().fillna(pos.abs()).sum(axis=1) * 10.0 / 1e4
roll = pos.abs().sum(axis=1).where(R.index.hour == 21, 0.0) * 3.3 / 1e4
h2 = ((pos * R).sum(axis=1) - turn - roll).reindex(IDX).fillna(0.0)
rows.append({"variant": "2x spread (10 bp)", "signals": ev, "DEV 2022": dsh(h2, "2022", "2022-12-31"), "TEST": dsh(h2, "2023", "2024-12-31"),
             "HOLD": dsh(h2, "2025", "2026-09-30"), "2022-26": dsh(h2, "2022", "2026-09-30")}); print(rows[-1], flush=True)
# trade list and top-5 removal
h, _ = run(); d = h.groupby(h.index.floor("D")).sum(); d = d[d != 0]
blocks = (d.index.to_series().diff() != pd.Timedelta(days=1)).cumsum(); ep = d.groupby(blocks.values).sum()
print("episodes", len(ep), "hit", round((ep > 0).mean(), 3), "mean bp", round(ep.mean() * 1e4, 1), "t-stat", round(ep.mean() / ep.std() * np.sqrt(len(ep)), 2), flush=True)
top = ep.sort_values().index[-5:]; d2 = d[~np.isin(blocks.values, top)]
full = h.groupby(h.index.floor("D")).sum().loc["2022":]; full2 = full.copy(); full2.loc[d.index[np.isin(blocks.values, top)]] = 0.0
rows.append({"variant": "without the 5 best episodes", "DEV 2022": np.nan, "2022-26": float(full2.mean() / full2.std() * np.sqrt(365)),
             "episodes": len(ep), "t-stat": float(ep.mean() / ep.std() * np.sqrt(len(ep)))}); print(rows[-1], flush=True)
print(ep.groupby(pd.Index([d.index[blocks.values == b][0].year for b in ep.index])).agg(["count", "mean", "sum"]).round(4), flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen89_check.csv", index=False)

"""Gen252 (config/gen252_protocol.json): swap-free TSMOM on FX / metals / energy CFDs in bf2. Writes results/gen252.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
END = "2026-09-30"
g = {"__file__": str(ROOT / "scripts/gen196_bf_ridge.py")}; exec(open(ROOT / "scripts/gen196_bf_ridge.py").read().split("\nIS = (P6 + R1)")[0], g)
CS, HB0, per, sh, hb, P6, R1, IDXbf = (g[k] for k in ("CS", "HB0", "per", "sh", "hb", "P6", "R1", "IDXbf"))
q = {"__file__": str(ROOT / "scripts/gen232_bf_p1.py")}; exec(open(ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], q)
P1, hourly = q["p1"](), q["hourly"]
book = lambda cols: CS.portfolio_v5(pd.concat(cols, axis=1).fillna(0.0))[0]
IS0 = (P6 + R1 + P1).rename("vol-managed indices"); hbr = hb.rename("ridge ML")
bf2 = book([HB0, IS0, hbr]); B0, k0 = sh(bf2, "2022-01-01", END), per(bf2, "2022-01-01")
COST = {**{s: 1e-4 for s in ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD")}, "XAUUSD": 2e-4, "XAGUSD": 2e-4,
        "WTI": 3e-4, "BRENT": 3e-4, "NATGAS": 3e-4}
closes = {s: hourly(s)["close"] for s in COST}
dc = pd.DataFrame({s: c.groupby(c.index.floor("D")).last() for s, c in closes.items()})
dc = dc[dc.index.weekday < 5].loc[:END]
sig = sum(np.sign(dc / dc.shift(n) - 1) for n in (21, 63, 252)) / 3
vol = dc.pct_change(fill_method=None).rolling(60, min_periods=40).std() * np.sqrt(252)
w = (sig * (0.10 / vol).clip(upper=2)).div(sig.notna().sum(axis=1), axis=0).fillna(0.0)
# daily P&L (pre-check 2014-19): weight decided at close d, earns d -> next trading day
rd = dc.pct_change(fill_method=None).fillna(0.0)
pnl_d = (w.shift(1) * rd).sum(axis=1) - (w.diff().abs() * pd.Series(COST)).sum(axis=1)
sh_d = lambda a, b: float(pnl_d.loc[a:b].mean() / pnl_d.loc[a:b].std() * np.sqrt(252))
# hourly version on the bf grid
legs = []
for s in COST:
    r = closes[s].reindex(IDXbf).ffill(limit=72).pct_change().fillna(0.0)
    wd = w[s].reindex(pd.date_range(w.index[0], IDXbf[-1].normalize())).ffill()       # weekend: keep Friday's weight
    wh = wd.shift(1).reindex(IDXbf.floor("D")).set_axis(IDXbf).fillna(0.0)
    legs.append(wh * r - wh.diff().abs().fillna(0.0) * COST[s])
T = sum(legs); p = per(T, "2020-01-01")
vb = book([HB0, IS0, hbr, T.rename("swap-free TSMOM")]); B1, k1 = sh(vb, "2022-01-01", END), per(vb, "2022-01-01")
out = {"reference bf2": [round(B0, 3), np.round(k0, 3).tolist()], "sleeve 2014-19 (daily)": round(sh_d("2014-01-01", "2019-12-31"), 3),
       "sleeve D/T/H": np.round(p, 3).tolist(), "corr with bf2": round(float(pd.concat([T, bf2], axis=1).dropna().resample("D").sum().corr().iloc[0, 1]), 3),
       "book": [round(B1, 3), np.round(k1, 3).tolist()]}
out["pass"] = bool(out["sleeve 2014-19 (daily)"] > 0 and p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen252.json", "w"), indent=1)

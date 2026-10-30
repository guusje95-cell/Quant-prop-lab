"""v9.9 R5 (research/v99/r5_protocol.json): US spot-bitcoin ETF flow impulse as a BTC sleeve of v9.8. Writes results/v99/r5_etf_flows.json."""
import glob
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B
T = pd.read_html(glob.glob(str(ROOT / "research_data/etf/*.htm*"))[0])[0]
T = T[pd.to_datetime(T["Date"], format="%d %b %Y", errors="coerce").notna()].copy()
val = lambda s: pd.to_numeric(s.astype(str).str.replace(",", "").str.replace(r"^\((.*)\)$", r"-\1", regex=True).replace("-", "0"), errors="coerce")
flow = pd.Series(val(T["Total"]).to_numpy(), index=pd.to_datetime(T["Date"], format="%d %b %Y")).sort_index()
flow = flow[flow.index <= "2026-09-30"]
f5 = flow.rolling(5).sum(); z = f5 / f5.rolling(120, min_periods=60).std().shift(1)
pos_d = (0.5 * (z / 2).clip(-1, 1)).dropna()
pos_d.index = pos_d.index + pd.Timedelta(days=2)                         # usable from 00:00 UTC of D+2
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
p = pos_d.reindex(idx.union(pos_d.index)).ffill().reindex(idx).fillna(0.0)
c = B.k5("BTC").close.resample("1h").last().reindex(idx).ffill(); r = c.pct_change().fillna(0.0)
fu = B.funding("BTC"); fu.index = pd.DatetimeIndex(fu.index).floor("h"); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
pnl = (p.shift(1) * r - p.diff().abs().fillna(p.abs()) * 6e-4 - p.shift(1) * fu).fillna(0.0)
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z_="2026-09-30"):
    d = dd(h.loc[a:z_]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025")]
s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
b0 = unit(CS.portfolio_v5(V8)[0]); b1 = unit(CS.portfolio_v5(V8.assign(**{"ETF flows": pnl}))[0])
btc_d = c.resample("1D").last().pct_change()
fd = flow.copy(); fd.index = fd.index.normalize()
out = {"days of flow data": int(flow.notna().sum()), "sleeve 2024 / 2025-26": [shp(pnl, "2024", "2024"), shp(pnl, "2025")],
       "sleeve by year": {str(y): shp(pnl, str(y), str(y)) for y in (2024, 2025, 2026)},
       "corr flow vs same-day BTC return": round(float(fd.corr(btc_d.reindex(fd.index))), 3),
       "corr flow vs next-day BTC return": round(float(fd.corr(btc_d.shift(-1).reindex(fd.index))), 3),
       "corr sleeve vs v9.8 (daily)": round(float(dd(pnl).loc["2024":].corr(dd(b0).loc["2024":])), 3),
       "reference v9.8": [shp(b0), per(b0)], "book with ETF flows": [shp(b1), per(b1)]}
out["pass"] = bool(out["book with ETF flows"][0] >= out["reference v9.8"][0] + 0.05 and all(out["book with ETF flows"][1][i] >= out["reference v9.8"][1][i] for i in range(3)))
(ROOT / "results/v99/r5_etf_flows.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

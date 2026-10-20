"""Gen147 (config/gen147_protocol.json): R1 dip-buying ensemble on index CFDs as a bf + P6 sleeve. Writes results/gen147.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen111_xexch.py")}
exec(open(ROOT / "scripts/gen111_xexch.py").read().split("\nw = pd.DataFrame(0.0, index=days")[0], g)
CS, HB0, per, sh, IDXbf = (g[k] for k in ("CS", "HB0", "per", "sh", "IDXbf"))
DUK = ROOT / "research_data/dukascopy"


def hourly(s):
    x = pd.read_parquet(DUK / f"{s}_1h.parquet").astype("float64"); x = x[~x.index.duplicated()].sort_index(); return x[x.close > 0]


def p6():
    legs = []
    for s in ("US100", "US500"):
        x = hourly(s)["close"].reindex(IDXbf).ffill(limit=72); r = x.pct_change().fillna(0.0)
        dret = r.groupby(r.index.floor("D")).sum(); vol = dret.rolling(20).std() * np.sqrt(252)
        wh = (0.5 * (0.15 / vol).clip(upper=2.0)).shift(1).reindex(IDXbf.floor("D")).set_axis(IDXbf).fillna(0.0)
        legs.append(wh * r - wh.diff().abs().fillna(0.0) * 1e-4)
    return sum(legs)


def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def r1(cost):
    legs = []
    for s in ("US100", "US500", "US30"):
        x = hourly(s); et = x.index.tz_localize("UTC").tz_convert("America/New_York"); d = pd.Series(pd.DatetimeIndex(et.date), index=x.index)
        wk = et.weekday < 5; snap = wk & (et.hour == 13); rth = wk & (et.hour >= 9) & (et.hour <= 13)
        c = x.close[snap].groupby(d[snap]).last()
        hi = x.high[rth].groupby(d[rth]).max().reindex(c.index); lo = x.low[rth].groupby(d[rth]).min().reindex(c.index)
        ibs = (c - lo) / (hi - lo)
        ind = [(rsi2(c) < 10), (c <= c.rolling(5).min()), (c.diff().lt(0).rolling(3).sum() == 3), (ibs < 0.3)]
        sig = 0.25 * (sum(z.astype(float) for z in ind) / 4).where(hi > lo, 0.0)
        # the position starts with the bar that opens at 14:00 ET on the signal day
        start = pd.Series(sig.to_numpy(), index=x.index[snap][~d[snap].duplicated(keep="last").to_numpy()] + pd.Timedelta(hours=1))
        px = x.close.reindex(IDXbf).ffill(limit=72); r = px.pct_change().fillna(0.0)
        wh = start.reindex(IDXbf.union(start.index)).ffill().reindex(IDXbf).fillna(0.0)
        legs.append(wh * r - wh.diff().abs().fillna(0.0) * cost)
    return sum(legs)


P6 = p6(); base = CS.portfolio_v5(pd.concat([HB0, P6.rename("vol-managed indices")], axis=1).fillna(0.0))[0]
B0, k0 = sh(base, "2022-01-01", "2026-09-30"), per(base, "2022-01-01")
out = {"bf + P6": [round(B0, 3), np.round(k0, 3).tolist()]}
for cost in (1e-4, 2e-4):
    sl = r1(cost); vb = CS.portfolio_v5(pd.concat([HB0, P6.rename("vol-managed indices"), sl.rename("dip ensemble")], axis=1).fillna(0.0))[0]
    p = per(sl, "2020-01-01"); k1 = per(vb, "2022-01-01"); B1 = sh(vb, "2022-01-01", "2026-09-30")
    res = {"sleeve D/T/H": np.round(p, 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()],
           "corr with bf + P6": round(float(pd.concat([sl, base], axis=1).dropna().resample("D").sum().corr().iloc[0, 1]), 3)}
    res["pass"] = bool(p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
    out[f"cost {cost * 1e4:.0f} bp"] = res
    if cost == 1e-4:
        vb.to_frame("book").to_parquet(ROOT / "results/gen147_book.parquet")
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen147.json", "w"), indent=1)

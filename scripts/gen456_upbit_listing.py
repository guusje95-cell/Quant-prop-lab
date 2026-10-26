"""Gen456 (config/gen456_protocol.json): Upbit listings merged into the listing short. Writes results/gen456.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
import pit_universe as PU
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, EVB = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
MORE = ROOT / "research_data/more"; EVU = []
for f in sorted(MORE.glob("upbit_KRW-*_1h.parquet")):
    base = f.name[len("upbit_KRW-"):-len("_1h.parquet")]
    t_up = pd.DatetimeIndex(pd.read_parquet(f, columns=["close"]).index).min()
    if t_up < pd.Timestamp("2021-06-01") or base in PU.TF or base in ("BTC", "ETH"):
        continue
    c = base if (PU.PIT / f"{base}USDT_1h.parquet").exists() or base in PU.PACK or base in PU.EXTRA else ("1000" + base if (PU.PIT / f"1000{base}USDT_1h.parquet").exists() else None)
    if c is None:
        continue
    rf = PU.ret_funding(c); fr = PU.frame(c) if c not in PU.PACK else None
    if c in PU.PACK:
        from qpl.lab import binance_pack as B
        close = B.k5(c).close.resample("1h").last()
    elif c in PU.EXTRA:
        close = pd.read_parquet(PU.EX / f"{c}USDT_1h.parquet")["close"].astype(float)
    else:
        close = pd.read_parquet(PU.PIT / f"{c}USDT_1h.parquet")["close"].astype(float)
    close.index = pd.DatetimeIndex(close.index).as_unit("ns")
    if close.index.min() > t_up - pd.Timedelta(days=7):
        continue                                                   # Binance perp not yet trading 7 days before the Upbit listing
    f_ = rf[1].copy() if rf is not None else pd.Series(dtype=float); f_.index = f_.index + pd.Timedelta(hours=1)   # back to stamp times for listing_live
    EVU.append((f"UPBIT_{c}USDT", t_up, close, f_))
LL.CAP = 1e9
P = pd.concat([LL.positions(idx, EVB), LL.positions(idx, EVU)], axis=1).T.groupby(level=0).min().T.reindex(idx).fillna(0.0)
g = P.abs().sum(axis=1); P = P.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
CF = {s[:-4]: (c, f) for s, t0, c, f in EVB}
CF.update({s[:-4]: (c, f) for s, t0, c, f in EVU})
s_ = pd.Series(0.0, index=idx)
for n in P.columns:
    c, f = CF[n]; p = P[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
    fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
    s_ = s_ + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 / 1e4
b = unit(CS.portfolio_v5(V7.assign(**{"listing short": s_}))[0]); r = [shp(b), per(b)]
r30 = []
for s, t0, c, f in EVU:
    st = (t0 + pd.Timedelta(hours=24)).ceil("D"); cc = c.loc[st:st + pd.Timedelta(days=30)]
    if len(cc) > 600:
        r30.append((st.year, float(cc.iloc[-1] / cc.iloc[0] - 1)))
R = pd.DataFrame(r30, columns=["y", "r"])
out = {"reference v9.7": [REF[0], REF[1]], "Upbit listing events": len(EVU), "median 30-day return after the Upbit listing by year": {str(y): [round(float(x.median()), 3), int(len(x))] for y, x in R.groupby("y")["r"]},
       "sleeve": per(s_), "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen456.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

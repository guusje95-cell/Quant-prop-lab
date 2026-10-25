"""Gen378 (config/gen378_protocol.json). Writes results/gen378.json.   cd scripts && python gen378_batch.py <v86 dump>"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
DUMP = sys.argv[1]; sys.argv = sys.argv[:1]
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
g = {"__file__": str(ROOT / "scripts/gen373_honest_cstar.py")}
s373 = open(ROOT / "scripts/gen373_honest_cstar.py").read().split("\nout = {")[0].replace("DUMP = sys.argv[1]; sys.argv = sys.argv[:1]", f"DUMP = {DUMP!r}")
exec(compile(s373, "g373", "exec"), g)
CS, B, H0, END = g["CS"], g["B"], g["H0"], g["END"]
from qpl.lab import extra_pack as X
ND = ROOT / "research_data/newdata"
dd = lambda h: h.groupby(h.index.floor("D")).sum()
shp = lambda h, a="2022", z=END: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
K1C = ["C*", "cascade limit strict", "trend 4h", "Weiss expiry", "delev bounce", "ridge ML", "alt kimchi"]
base = H0[K1C].assign(**{"C*": g["cp"]}); K1 = unit(CS.portfolio_v5(base)[0]); REF = (shp(K1), per(K1))
days = pd.date_range("2020-01-01", END[:10], freq="D")
z = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
def daily(s, how="last"):
    s = s.copy(); s.index = pd.DatetimeIndex(s.index).floor("D"); s = getattr(s.groupby(level=0), how)()
    return s.reindex(days).ffill().shift(1)
W = {}
fa, fb = {}, {}
for c in ("BTC", "ETH"):
    by = pd.read_parquet(ROOT / f"research_data/bybit/funding/{c}USDT.parquet")["funding_rate"]; by.index = pd.DatetimeIndex(by.index)
    bn = B.funding(c)
    dv = (daily(by, "sum") - daily(bn, "sum")).rolling(7).mean(); fa[c] = -0.125 * z(dv, 90).clip(-2, 2) / 2
    px = B.k5(c).close.resample("1D").last()
    oi_by = pd.read_parquet(ND / f"bybit_{c}_oi_1d.parquet")["openInterest"]; oi_by.index = pd.DatetimeIndex(oi_by.index).floor("D")
    oi_by = (oi_by * px.reindex(oi_by.index)).reindex(days)
    oi_bn = B.metrics(c)["sum_open_interest_value"].resample("1D").last().reindex(days)
    share = (oi_by / (oi_by + oi_bn)).shift(1); fb[c] = -0.125 * z(share.diff(7), 90).clip(-2, 2) / 2
W["A funding divergence"] = pd.DataFrame(fa); W["B OI share divergence"] = pd.DataFrame(fb)
mp = daily(pd.read_parquet(ND / "bc_mempool-size.parquet")["mempool-size"], "mean")
W["C mempool congestion"] = pd.DataFrame({"BTC": -0.25 * z(mp, 90).clip(-2, 2) / 2})
out = {"reference K1": [REF[0], REF[1]]}; res = {}
for nm, w in W.items():
    h = CS._from_daily_weights(w.reindex(days).fillna(0.0), list(w.columns), 5).reindex(H0.index).fillna(0.0)
    b = unit(CS.portfolio_v5(base.assign(**{nm: h}))[0]); B1, k = shp(b), per(b); s = per(h)
    res[nm] = {"sleeve 2022 / 2023-24 / 2025-26": s, "corr with K1": round(float(pd.concat([dd(h), dd(K1)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3),
               "K1 + sleeve": [B1, k], "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)) and s[0] > 0 and s[1] > 0)}
    print(nm, res[nm], flush=True)
# D: trend 4h on the point-in-time top-10 (candidates: pack + extra)
cands = CS._breadth_universe()
def ohlc(c):
    if c in B.coins():
        k = B.k5(c); return k.close.resample("1h").last(), k.high.resample("1h").max(), k.low.resample("1h").min(), k.quote_volume.resample("1h").sum()
    d = pd.read_parquet(X.PACK / f"{c}USDT_1h.parquet"); d.index = pd.DatetimeIndex(d.index); d = d[~d.index.duplicated()]
    return d.close.astype(float), d.high.astype(float), d.low.astype(float), d.quote_volume.astype(float)
OH = {c: ohlc(c) for c in cands}
Dc = pd.DataFrame({c: OH[c][0] for c in cands}).loc[:END].resample("1D").last(); QV = pd.DataFrame({c: OH[c][3] for c in cands}).loc[:END].resample("1D").sum().reindex(Dc.index)
dv = QV.rolling(30, min_periods=20).sum().shift(1); elig = Dc.notna().cumsum().shift(1) >= 200; mf = ~Dc.index.to_period("M").duplicated()
mem = (dv.where(elig).rank(axis=1, ascending=False) <= 10)[mf].reindex(Dc.index).ffill().fillna(False).astype(bool)
pn = {}
for c in cands:
    cl, hi, lo, _ = OH[c]; c4 = cl.resample("4h").last().loc[:END]; h4 = hi.resample("4h").max().loc[c4.index]; l4 = lo.resample("4h").min().loc[c4.index]
    hi_in, lo_in = h4.rolling(20).max().shift(1).to_numpy(), l4.rolling(20).min().shift(1).to_numpy()
    hi_out, lo_out = h4.rolling(10).max().shift(1).to_numpy(), l4.rolling(10).min().shift(1).to_numpy()
    cv = c4.to_numpy(); pos = np.zeros(len(cv)); p = 0
    for i in range(len(cv)):
        if p == 0:
            p = 1 if cv[i] > hi_in[i] else (-1 if cv[i] < lo_in[i] else 0)
        elif p == 1 and cv[i] < lo_out[i]:
            p = 0
        elif p == -1 and cv[i] > hi_out[i]:
            p = 0
        pos[i] = p
    r4 = c4.pct_change().fillna(0); lev = (0.10 / (r4.rolling(180).std().shift(1) * np.sqrt(6 * 365))).clip(upper=2.0).fillna(0)
    held4 = pd.Series(pos, index=c4.index) * lev; held4.index = held4.index + pd.Timedelta(hours=4)
    h1 = cl.loc[:END]; held = held4.reindex(h1.index, method="ffill").fillna(0)
    m = mem[c].shift(1).reindex(h1.index.floor("D")).fillna(False).to_numpy()            # membership known at the previous close
    held = held.where(m, 0.0)
    f = (B.funding(c) if c in B.coins() else X.funding(c)).copy(); f.index = f.index - pd.Timedelta(hours=1); f = f.groupby(level=0).sum().reindex(h1.index).fillna(0.0)
    pn[c] = held * h1.pct_change().fillna(0) - held * f - held.diff().abs().fillna(0) * 5 / 1e4
td = pd.DataFrame(pn).fillna(0).sum(axis=1) / 10
td = td.reindex(H0.index).fillna(0.0)
b = unit(CS.portfolio_v5(base.assign(**{"trend 4h": td}))[0]); B1, k = shp(b), per(b)
res["D trend 4h point-in-time"] = {"sleeve 2022 / 2023-24 / 2025-26": per(td), "current trend 4h": per(H0["trend 4h"]), "K1 with it": [B1, k],
                                   "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
print("D", res["D trend 4h point-in-time"], flush=True)
out["trials"] = res; (ROOT / "results/gen378.json").write_text(json.dumps(out, indent=1)); print("DONE")

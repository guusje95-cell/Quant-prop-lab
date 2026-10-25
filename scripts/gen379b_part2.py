"""Gen379b part 2 (config/gen379b_protocol.json), memory-light rebuild of the 5 basket members with a cost multiplier and lag.
Appends to results/gen379b.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
from qpl.lab.data import stablecoin_caps
END = "2026-09-30"; ND = ROOT / "research_data/newdata"
idx = pd.date_range("2022-01-01", END + " 23:00", freq="h"); days = pd.date_range("2019-06-01", END, freq="D")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
shp = lambda h, a="2022", z=END: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
z = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
def daily(s, how="last"):
    s = s.copy(); s.index = pd.DatetimeIndex(s.index).floor("D"); s = getattr(s.groupby(level=0), how)()
    return s.reindex(days).ffill().shift(1)
def rdp(f):
    x = pd.read_parquet(f); x.index = pd.DatetimeIndex(x.index); return x[~x.index.duplicated()].sort_index()
R = {c: B.k5(c).close.resample("1h").last().pct_change().fillna(0.0) for c in ("BTC", "ETH")}
FU = {}
for c in ("BTC", "ETH"):
    f = B.funding(c).copy(); f.index = f.index - pd.Timedelta(hours=1); FU[c] = f.groupby(level=0).sum()
def hourly_pnl(Ph, cm):                                   # Ph: hourly positions per coin
    out = 0.0
    for c in Ph:
        p = Ph[c].reindex(idx).fillna(0.0); r = R[c].reindex(idx).fillna(0.0); f = FU[c].reindex(idx).fillna(0.0)
        out = out + p * r - p * f - p.diff().abs().fillna(0.0) * 5 * cm / 1e4
    return out
def from_daily(W, lag_days):                              # row d decided at the close of d, held during d+1 (+ lag)
    W = W.fillna(0.0).shift(1 + lag_days)
    return {c: W[c].reindex(idx.floor("D")).set_axis(idx) for c in W}
def members(cm=1.0, lag_h=0):
    lag_d = 1 if lag_h else 0; P = {}
    cap = stablecoin_caps(); cap = cap.where(cap > 0).loc["2019":]; gg = cap.pct_change().shift(2).reindex(days)
    sig = (gg > 0.005).astype(float).rolling(3, min_periods=1).max()
    P["mint shock"] = hourly_pnl(from_daily(pd.DataFrame({"BTC": 0.5 * sig, "ETH": 0.5 * sig}), lag_d), cm)
    pos = {}
    for c in ("BTC", "ETH"):
        cb = rdp(ROOT / f"research_data/coinbase/{c}-USD_1h.parquet")["close"].reindex(idx); sp = rdp(ROOT / f"research_data/binance_spot/{c}USDT_1h.parquet")["close"].reindex(idx)
        pr = cb / sp - 1; zz = (pr - pr.rolling(720, min_periods=500).mean().shift(1)) / pr.rolling(720, min_periods=500).std().shift(1)
        s = np.where(zz > 2, 0.5, np.where(zz < -2, -0.5, 0.0)); o = np.zeros(len(s))
        for t in np.flatnonzero(s != 0):
            o[t + 1 + lag_h:min(t + 5 + lag_h, len(s))] = s[t]
        pos[c] = pd.Series(o, index=idx)
    P["Coinbase hourly premium"] = hourly_pnl(pos, cm)
    st = daily(pd.read_parquet(ND / "defillama_stablecoins.parquet")["stablecoin_usd"]); n2 = z(np.log(st).diff(30), 365)
    P["stablecoin impulse"] = hourly_pnl(from_daily(pd.DataFrame({"BTC": 0.125 * n2.clip(-2, 2) / 2, "ETH": 0.125 * n2.clip(-2, 2) / 2}), lag_d), cm)
    n3 = z(daily(pd.read_parquet(ND / "bc_transaction-fees-usd.parquet")["transaction-fees-usd"]), 90)
    P["fee pressure"] = hourly_pnl(from_daily(pd.DataFrame({"BTC": -0.25 * n3.clip(-2, 2) / 2}), lag_d), cm)
    P["Bybit crowding"] = hourly_pnl(from_daily(pd.DataFrame({c: -0.25 * z(daily(pd.read_parquet(ND / f"bybit_{c}_account_ratio_1d.parquet")["buyRatio"]), 90).clip(-2, 2) / 2 for c in ("BTC", "ETH")}), lag_d), cm)
    return P
def basket(P, keys=None):
    keys = keys or list(P); Dk = pd.DataFrame({k: dd(P[k]) for k in keys}); sdv = Dk.loc[:"2024"].std()
    return sum(P[k] / sdv[k] for k in keys)
P0 = members(); b0 = basket(P0)
ref = pd.read_parquet(ROOT / "results/gen379_basket_hourly.parquet")["basket"]
d = dd(b0).loc["2022":END]
out = {"check: corr with the Gen379 basket (daily)": round(float(pd.concat([d, dd(ref)], axis=1).dropna().corr().iloc[0, 1]), 3),
       "basket 2022-26": shp(b0), "by calendar year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.groupby(d.index.year)},
       "costs x2 (2022-26)": shp(basket(members(cm=2.0))), "one day later (daily members) / one hour later (hourly member), 2022-26": shp(basket(members(lag_h=1))),
       "leave one member out (2022-26)": {k: shp(basket(P0, [x for x in P0 if x != k])) for k in P0}}
out["positive years"] = int(sum(v > 0 for v in out["by calendar year"].values()))
print(json.dumps(out, indent=1))
r = json.loads((ROOT / "results/gen379b.json").read_text()) if (ROOT / "results/gen379b.json").exists() else {}
r["part 2"] = out; r["v9.1 candidate"] = False; r["note"] = "part 1 failed (the 2022-24 choice is m = 1.0, 2023-24 lower), so the basket is not a candidate whatever part 2 shows"
(ROOT / "results/gen379b.json").write_text(json.dumps(r, indent=1))

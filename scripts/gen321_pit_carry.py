"""Gen321 (config/gen321_protocol.json): the wide invvol premium carry on a point-in-time top-60-by-volume universe that includes
delisted perps (research_data/binance_pit). Writes results/gen321.json. Without the pit data it runs on pack + extra only (a code check:
it should then come close to Gen316)."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
from qpl.lab import binance_pack as B, extra_pack as X
END = L.END; PIT = L.ROOT / "research_data/binance_pit"
pit = sorted(p.stem.replace("USDT_1h", "") for p in PIT.glob("*USDT_1h.parquet")) if PIT.exists() else []


def series(c):
    """hourly close, hourly quote volume, hourly premium, funding (8h) for any coin."""
    if c in B.coins():
        k = B.k5(c); return (k.close.resample("1h").last(), k.quote_volume.resample("1h").sum(), B.premium(c)["close"], B.funding(c))
    if c in X.coins():
        d = pd.read_parquet(X.PACK / f"{c}USDT_1h.parquet")
        return (X.close_1h(c), d["quote_volume"].astype(float), X.premium(c), X.funding(c))
    d = pd.read_parquet(PIT / f"{c}USDT_1h.parquet"); d.index = pd.DatetimeIndex(d.index)
    pr = pd.read_parquet(PIT / f"{c}USDT_premium_1h.parquet") if (PIT / f"{c}USDT_premium_1h.parquet").exists() else None
    pr = pr.set_index(pd.to_datetime(pr["time"]))["close"].astype(float) if pr is not None else pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    fu = pd.read_parquet(PIT / f"{c}USDT_funding.parquet") if (PIT / f"{c}USDT_funding.parquet").exists() else None
    fu = fu.set_index(pd.to_datetime(fu["time"]))["last_funding_rate"].astype(float) if fu is not None else pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    return d["close"].astype(float), d["quote_volume"].astype(float), pr, fu


coins = sorted(set(B.coins()) | set(X.coins()) | set(pit))
S = {c: series(c) for c in coins}
H = pd.DataFrame({c: s[0] for c, s in S.items()}).sort_index().loc["2020-01-01":END + " 23:00"]
QV = pd.DataFrame({c: s[1] for c, s in S.items()}).reindex(H.index).resample("1D").sum()
P = H.resample("1D").last(); listed = P.notna().cumsum() >= 60
live = P.notna() & P.ffill().notna()                                                   # the coin still has a price that day
mon = QV.rolling(30, min_periods=20).sum().where(listed & live)
uni = mon.rank(axis=1, ascending=False).le(60)                                          # top 60 by trailing volume (daily, used at rebalances)
prem = pd.DataFrame({c: S[c][2].resample("1D").mean() for c in coins}).reindex(P.index).rolling(7).mean()
rk = (-prem).where(uni).rank(axis=1, pct=True); iv = (1 / P.pct_change(fill_method=None).rolling(30).std()).where(uni)
wl, ws = iv.where(rk > 2 / 3, 0.0), iv.where(rk <= 1 / 3, 0.0)
w = wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)
w = w.where(pd.Series(np.arange(len(w)) % 7 == 0, index=w.index), np.nan).ffill().fillna(0.0)
r = H.pct_change(fill_method=None).fillna(0.0)
wd = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)
held = wd.reindex(H.index.floor("D")).set_axis(H.index).fillna(0.0).where(H.ffill().notna(), 0.0)   # delisted: flat after the last price
F = pd.DataFrame({c: S[c][3] for c in coins}); F.index = F.index - pd.Timedelta(hours=1); F = F.groupby(level=0).sum().reindex(H.index).fillna(0.0)
turn = wd.fillna(0.0).diff().abs().sum(axis=1).reindex(H.index.floor("D")).set_axis(H.index).where(H.index.hour == 0, 0.0)
h = (held * r).sum(axis=1) - (held * F).sum(axis=1) - turn.fillna(0.0) * 5 / 1e4
out = {"pit coins available": len(pit), "universe size (mean)": float(uni.sum(axis=1).loc["2021":].mean()),
       "coins ever in the universe": int(uni.any().sum()), "reference v8.5": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
REF84 = (2.750, [1.324, 3.896, 2.428])
b = L.CS.portfolio_v5(pd.concat([L.H6, L.RIDGE] + [a for a in L.ALTK if a.name != "premium carry 60"] + [h.reindex(L.H6.index).fillna(0.0).rename("premium carry pit")], axis=1).fillna(0.0))[0]
B1, k = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
out["sleeve D/T/H"] = np.round(L.per(h.reindex(L.H6.index).fillna(0.0), "2020-01-01"), 3).tolist()
out["v8.4 + point-in-time carry"] = [round(B1, 3), np.round(k, 3).tolist()]
out["v8.5 confirmed"] = bool(B1 > REF84[0] and k[1] >= REF84[1][1] and k[2] >= REF84[1][2])
print(out); json.dump(out, open(L.ROOT / "results/gen321.json" if pit else L.ROOT / "results/gen321_codecheck.json", "w"), indent=1)

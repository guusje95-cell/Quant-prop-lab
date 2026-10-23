"""Gen347 (config/gen347_protocol.json): taker-flow reversal on perps (58 coins) and spot flow (18 coins), excluding BTC/ETH.
Writes results/gen347.json and results/gen347_series.parquet."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
from qpl.lab import binance_pack as B, extra_pack as X
END = L.END; ROOT = L.ROOT
coins = CS._breadth_universe(); Hc = CS._breadth_close(coins).loc[:END + " 23:00"]; R = Hc.pct_change(fill_method=None).fillna(0.0); idx = Hc.index
pk = B.coins()
fund = pd.concat([B.funding_panel(pk)] + [X.funding(c).rename(c) for c in coins if c not in pk], axis=1).sort_index()[coins]
fund.index = fund.index - pd.Timedelta(hours=1); fund = fund.groupby(level=0).sum().reindex(idx).fillna(0.0)
OTH = [c for c in coins if c not in ("BTC", "ETH")]


def rd(f):
    x = pd.read_parquet(f); x.index = pd.DatetimeIndex(x.index); return x[~x.index.duplicated()].sort_index()


def share(c, kind):
    if kind == "spot":
        d = rd(ROOT / f"research_data/binance_spot/{c}USDT_1h.parquet")
    elif c in pk:
        k = B.k5(c); d = k[["volume", "taker_buy_volume"]].resample("1h").sum()
    else:
        d = rd(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")
    return (d["taker_buy_volume"] / d["volume"].replace(0, np.nan)).reindex(idx)


def positions(cs, kind, lag=0):
    P = np.zeros((len(idx), len(coins))); n = len(idx)
    for c in cs:
        s = share(c, kind); z = ((s - s.rolling(720, min_periods=500).mean().shift(1)) / s.rolling(720, min_periods=500).std().shift(1)).to_numpy()
        j = coins.index(c)
        for t in np.flatnonzero(np.abs(np.nan_to_num(z)) > 2):
            P[t + 1 + lag:min(t + 4 + lag, n), j] = -0.1 * np.sign(z[t])
    return pd.DataFrame(P, index=idx, columns=coins)


def pnl(pos, cost=5.0):
    return (pos * R).sum(axis=1) - (pos * fund).sum(axis=1) - pos.diff().abs().fillna(0.0).sum(axis=1) * cost / 1e4


vd = L.V7.groupby(L.V7.index.floor("D")).sum(); out = {}; ser = {}
spot_coins = [c for c in pk if c not in ("BTC", "ETH")]
for nm, cs, kind in (("R1 perp flow, 58 coins", OTH, "perp"), ("R2 spot flow, 18 coins", spot_coins, "spot")):
    pos = positions(cs, kind); h = pnl(pos).reindex(L.H6.index).fillna(0.0); ser[nm] = h
    s = [round(x, 3) for x in L.per(h, "2020-01-01")]
    c = float(pd.concat([h.groupby(h.index.floor("D")).sum(), vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1])
    turn = float(pos.diff().abs().sum(axis=1).groupby(idx.floor("D")).sum().mean())
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6 2022-26": round(c, 3), "daily turnover (x unit)": round(turn, 2),
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2)}
    out[nm]["stress costs x2"] = [round(x, 3) for x in L.per(pnl(pos, 10.0).reindex(L.H6.index).fillna(0.0), "2020-01-01")]
    out[nm]["stress one hour later"] = [round(x, 3) for x in L.per(pnl(positions(cs, kind, lag=1)).reindex(L.H6.index).fillna(0.0), "2020-01-01")]
    print(nm, out[nm], flush=True)
out["FOUND (both pass)"] = bool(all(out[k]["pass"] for k in ("R1 perp flow, 58 coins", "R2 spot flow, 18 coins")))
pd.DataFrame(ser).to_parquet(ROOT / "results/gen347_series.parquet")
json.dump(out, open(ROOT / "results/gen347.json", "w"), indent=1); print(out["FOUND (both pass)"])

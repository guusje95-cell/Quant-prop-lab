"""Gen346 (config/gen346_protocol.json): hourly Coinbase premium, Upbit volume spikes, spot taker imbalance. Writes results/gen346.json."""
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


def pnl(pos):
    pos = pos.reindex(index=idx, columns=coins).fillna(0.0)
    return (pos * R).sum(axis=1) - (pos * fund).sum(axis=1) - pos.diff().abs().fillna(0.0).sum(axis=1) * 5 / 1e4


def hold(sig, k):                                                        # sig at bar t -> position over bars t+1..t+k (latest signal wins)
    out = pd.Series(0.0, index=sig.index); s = sig.to_numpy(); o = out.to_numpy().copy(); n = len(s)
    for t in np.flatnonzero(s != 0):
        o[t + 1:min(t + 1 + k, n)] = s[t]
    return pd.Series(o, index=sig.index)


def rd(f):
    x = pd.read_parquet(f); x.index = pd.DatetimeIndex(x.index); return x[~x.index.duplicated()].sort_index()


S = {}
pos = pd.DataFrame(0.0, index=idx, columns=coins)
for c in ("BTC", "ETH"):
    cb = rd(ROOT / f"research_data/coinbase/{c}-USD_1h.parquet")["close"].reindex(idx); sp = rd(ROOT / f"research_data/binance_spot/{c}USDT_1h.parquet")["close"].reindex(idx)
    pr = cb / sp - 1; z = (pr - pr.rolling(720, min_periods=500).mean().shift(1)) / pr.rolling(720, min_periods=500).std().shift(1)
    pos[c] = hold(pd.Series(np.where(z > 2, 0.5, np.where(z < -2, -0.5, 0.0)), index=idx), 4)
S["A Coinbase hourly premium"] = pnl(pos)
pos = pd.DataFrame(0.0, index=idx, columns=coins); ev = []
for c in coins:
    f = ROOT / f"research_data/more/upbit_KRW-{c.replace('1000', '')}_1h.parquet"
    if not f.exists():
        continue
    u = rd(f).reindex(idx); v = u["volume"]; r = u["close"].pct_change(fill_method=None)
    e = (v > 5 * v.rolling(168, min_periods=100).median().shift(1)) & (r > 0)
    ev += [(t, c) for t in np.flatnonzero(e.fillna(False).to_numpy())]
ev.sort(); P = pos.to_numpy().copy(); ends = []; col = {c: i for i, c in enumerate(coins)}; n = len(idx)
for t, c in ev:
    ends = [e for e in ends if e > t]
    if len(ends) >= 5 or t + 1 >= n:
        continue
    P[t + 1:min(t + 7, n), col[c]] += 0.1; ends.append(t + 6)
S["B Upbit volume spike"] = pnl(pd.DataFrame(P, index=idx, columns=coins))
S["B events"] = None
pos = pd.DataFrame(0.0, index=idx, columns=coins)
for c in ("BTC", "ETH"):
    sp = rd(ROOT / f"research_data/binance_spot/{c}USDT_1h.parquet").reindex(idx); sh_ = sp["taker_buy_volume"] / sp["volume"]
    z = (sh_ - sh_.rolling(720, min_periods=500).mean().shift(1)) / sh_.rolling(720, min_periods=500).std().shift(1)
    pos[c] = hold(pd.Series(np.where(z > 2, 0.5, np.where(z < -2, -0.5, 0.0)), index=idx), 3)
S["C spot taker imbalance"] = pnl(pos)
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); out = {"B Upbit spike events": len(ev)}
for nm, h in S.items():
    if h is None:
        continue
    h = h.reindex(L.H6.index).fillna(0.0); s = [round(x, 3) for x in L.per(h, "2020-01-01")]
    c = float(pd.concat([h.groupby(h.index.floor("D")).sum(), vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6 2022-26": round(c, 3), "orthogonal candidate": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2)}
    print(nm, out[nm], flush=True)
json.dump(out, open(ROOT / "results/gen346.json", "w"), indent=1)

"""Gen349 (config/gen349_protocol.json): Binance-OKX gap, Upbit hourly kimchi, ETH/BTC ratio spikes, DVOL spikes. Writes results/gen349.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
import ridge_live as RL
from qpl.lab import binance_pack as B, extra_pack as X
END = L.END; ROOT = L.ROOT
coins = CS._breadth_universe(); Hc = CS._breadth_close(coins).loc[:END + " 23:00"]; R = Hc.pct_change(fill_method=None).fillna(0.0); idx = Hc.index; n = len(idx)
pk = B.coins()
fund = pd.concat([B.funding_panel(pk)] + [X.funding(c).rename(c) for c in coins if c not in pk], axis=1).sort_index()[coins]
fund.index = fund.index - pd.Timedelta(hours=1); fund = fund.groupby(level=0).sum().reindex(idx).fillna(0.0)
pnl = lambda P, cost=5.0: (P * R).sum(axis=1) - (P * fund).sum(axis=1) - P.diff().abs().fillna(0.0).sum(axis=1) * cost / 1e4
zz = lambda g: ((g - g.rolling(720, min_periods=500).mean().shift(1)) / g.rolling(720, min_periods=500).std().shift(1)).to_numpy()


def spikes(G, sign, size=0.1, th=3.0, hold=4):
    P = np.zeros((n, len(coins)))
    for c, g in G.items():
        z = np.nan_to_num(zz(g.reindex(idx))); j = coins.index(c)
        for t in np.flatnonzero(np.abs(z) > th):
            P[t + 1:min(t + 1 + hold, n), j] = sign * size * np.sign(z[t])
    return pd.DataFrame(P, index=idx, columns=coins)


def rd(f):
    x = pd.read_parquet(f); x.index = pd.DatetimeIndex(x.index); return x[~x.index.duplicated()].sort_index()


S = {}
NM = {"1000PEPE": "PEPE", "1000SHIB": "SHIB"}; G = {}
for c in coins:
    f = ROOT / f"data/raw/okx/{NM.get(c, c)}-USDT-SWAP_1H.parquet"
    if f.exists():
        G[c] = Hc[c] / rd(f)["close"].reindex(idx) - 1
S["A Binance vs OKX perp"] = spikes(G, -1)
fx = RL.usdkrw().shift(1); G = {}
for c in coins:
    f = ROOT / f"research_data/more/upbit_KRW-{c.replace('1000', '')}_1h.parquet"
    if f.exists() and "1000" not in c:
        up = rd(f)["close"].reindex(idx); fxh = fx.reindex(idx.floor("D"), method="ffill").set_axis(idx)
        G[c] = up / fxh / Hc[c] - 1
S["B Upbit hourly kimchi"] = spikes(G, +1)
lr = np.log(Hc["ETH"] / Hc["BTC"]).diff(); z = np.nan_to_num(zz(lr)); P = np.zeros((n, len(coins))); ie, ib = coins.index("ETH"), coins.index("BTC")
for t in np.flatnonzero(np.abs(z) > 3):
    s = -np.sign(z[t]); P[t + 1:min(t + 5, n), ie] = 0.25 * s; P[t + 1:min(t + 5, n), ib] = -0.25 * s
S["C ETH/BTC hourly ratio spike"] = pd.DataFrame(P, index=idx, columns=coins)
dv = np.log(RL.dvol("BTC")).diff(); zd = (dv - dv.rolling(90, min_periods=60).mean().shift(1)) / dv.rolling(90, min_periods=60).std().shift(1)
days = pd.date_range("2019-06-01", END); sig = (zd.reindex(days) > 2).astype(float).rolling(3, min_periods=1).max()
hD = CS._from_daily_weights(pd.DataFrame({"BTC": 0.5 * sig, "ETH": 0.5 * sig}), ["BTC", "ETH"], 5).loc[:END + " 23:00"]
spike = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"]
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); sd_ = spike.groupby(spike.index.floor("D")).sum(); out = {}
for nm in list(S) + ["D DVOL spike (daily)"]:
    h = (pnl(S[nm]) if nm in S else hD).reindex(L.H6.index).fillna(0.0); s = [round(x, 3) for x in L.per(h, "2020-01-01")]
    d = h.groupby(h.index.floor("D")).sum()
    c = float(pd.concat([d, vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1]); c2 = float(pd.concat([d, sd_], axis=1).loc["2020-01-01":END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "corr premium spike": round(c2, 3),
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2 and abs(c2) <= 0.5)}
    if nm in S:
        out[nm]["gross"] = [round(x, 3) for x in L.per(pnl(S[nm], 0.0).reindex(L.H6.index).fillna(0.0), "2020-01-01")]
    print(nm, out[nm], flush=True)
    h.to_frame(nm).to_parquet(ROOT / f"results/gen349_{nm[0]}.parquet")
json.dump(out, open(ROOT / "results/gen349.json", "w"), indent=1)

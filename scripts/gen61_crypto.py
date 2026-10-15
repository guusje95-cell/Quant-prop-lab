"""Gen61 (config/gen61_protocol.json): remaining crypto ideas. G1 crowding overlay on C*, G2 funding-settlement window (maker),
G4 premium carry XS, G5 bear short sleeve, G12 Monday-anchored intraday trend. Writes results/gen61_crypto.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_timing as T
import crypto_sleeves as CS
from qpl.lab import binance_pack as B

rep = T.report
H = CS.all_sleeves(); cst = H["C*"].groupby(H.index.floor("D")).sum()

# G1 crowding overlay on C*: premium z (30d) and 7d OI-change z both above trailing 1y 95th pct -> halve; restore below 80th
pz = B.premium("BTC")["close"].resample("1D").mean(); pz = (pz - pz.rolling(30).mean()) / pz.rolling(30).std()
oi = B.metrics("BTC")["sum_open_interest_value"].resample("1D").last(); o7 = oi / oi.shift(7) - 1; oz = (o7 - o7.rolling(30).mean()) / o7.rolling(30).std()
q95p, q80p = pz.rolling(365, min_periods=120).quantile(0.95), pz.rolling(365, min_periods=120).quantile(0.80)
q95o, q80o = oz.rolling(365, min_periods=120).quantile(0.95), oz.rolling(365, min_periods=120).quantile(0.80)
state, m = False, {}
for d in pz.index:
    if not state and pz[d] > q95p.get(d, np.inf) and oz.get(d, -np.inf) > q95o.get(d, np.inf):
        state = True
    elif state and (pz[d] < q80p.get(d, -np.inf) or oz.get(d, np.inf) < q80o.get(d, -np.inf)):
        state = False
    m[d] = 0.5 if state else 1.0
mult = pd.Series(m).shift(1).reindex(cst.index).fillna(1.0)        # decided at the close, applied the next day
g1 = cst * mult
for name, x in (("G1 base: C* (perps, funding)", cst), ("G1 C* with crowding overlay", g1)):
    y = x.loc["2023":]; eq = (1 + y).cumprod(); dd = (eq / eq.cummax() - 1).min()
    print(name, "2023+ Sharpe", round(y.mean() / y.std() * np.sqrt(365), 3), "maxDD", round(dd, 3), "Calmar", round(y.mean() * 365 / -dd, 2), "days halved", int((mult < 1).sum()))
    rep(name, x)

# G2 funding-settlement window, maker 2 bp with 5-min touch rule
def settle(coin):
    k = B.k5(coin); f = B.funding(coin)
    out = {}
    for ts, rate in f.items():
        side = -1 if rate > 0.0003 else (1 if rate < -0.0001 else 0)
        if side == 0:
            continue
        t0 = ts + pd.Timedelta(hours=7); t1 = ts + pd.Timedelta(hours=9)          # next settlement = ts + 8h; window 1h before/after
        if t0 not in k.index or t1 not in k.index:
            continue
        o0, o1 = k.open[t0], k.open[t1]
        f0 = (k.low[t0] <= o0 * (1 - 1e-4)) if side > 0 else (k.high[t0] >= o0 * (1 + 1e-4))
        f1 = (k.high[t1] >= o1 * (1 + 1e-4)) if side > 0 else (k.low[t1] <= o1 * (1 - 1e-4))
        nxt = f.get(ts + pd.Timedelta(hours=8), 0.0)
        r = side * (o1 / o0 - 1) - side * nxt - (2 if f0 else 5) / 1e4 - (2 if f1 else 5) / 1e4
        d = t1.floor("D"); out[d] = out.get(d, 0.0) + r
    return pd.Series(out)


g2 = pd.concat([settle(c) for c in B.coins()], axis=1).fillna(0.0).mean(axis=1)
rep("G2 funding-settlement window, 20 coins (maker approx.)", g2)

# G4 premium carry XS (7d average premium index), hold 7d
C = B.coins(); P = B.panel("close", "1D", C); R = P.pct_change(fill_method=None)
F = B.funding_panel(C); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D"); FD = F.groupby(level=0).sum().reindex(P.index)
prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in C}).reindex(P.index).rolling(7).mean()
listed = P.notna().cumsum() >= 60
rk = (-prem).where(listed).rank(axis=1, pct=True)
w = (rk > 2 / 3).astype(float).div((rk > 2 / 3).sum(axis=1), axis=0) - (rk <= 1 / 3).astype(float).div((rk <= 1 / 3).sum(axis=1), axis=0)
w = w.where(pd.Series(np.arange(len(w)) % 7 == 0, index=w.index), np.nan).ffill().fillna(0.0)
hw = w.shift(1).fillna(0.0)
g4 = (hw * R.fillna(0) - hw * FD.fillna(0)).sum(axis=1) - hw.diff().abs().sum(axis=1) * 5e-4
rep("G4 premium carry XS (7d avg premium), hold 7d", g4)

# G5 bear short sleeve: short BTC+ETH when BTC < 50d MA and 100d MA falling vs 10 days ago; 10% vol; funding included
pb = P["BTC"]; ma50, ma100 = pb.rolling(50).mean(), pb.rolling(100).mean()
bear = (pb < ma50) & (ma100 < ma100.shift(10))
vol = R[["BTC", "ETH"]].rolling(30).std() * np.sqrt(365)
wv = (0.10 / vol).clip(upper=1.0) / 2
w5 = -wv.mul(bear.astype(float), axis=0)
h5 = w5.shift(1).fillna(0.0)
g5 = (h5 * R[["BTC", "ETH"]].fillna(0) - h5 * FD[["BTC", "ETH"]].fillna(0)).sum(axis=1) - h5.diff().abs().sum(axis=1) * 5e-4
rep("G5 bear short sleeve BTC+ETH", g5)
print("G5 2022 return:", round(float((1 + g5.loc["2022"]).prod() - 1), 3), " share of days short:", round(float(bear.mean()), 2))

# G12 noise-area intraday trend anchored at Sunday 23:00 UTC, trading Sunday 23:00 -> Monday 23:00 only
def monday_trend(coin, lookback=6, cost=5):
    k = B.k5(coin); c30 = k.close.resample("30min").last()
    starts = c30.index[(c30.index.dayofweek == 6) & (c30.index.hour == 23) & (c30.index.minute == 0)]
    moves = []; out = {}
    for s in starts:
        seg = c30.loc[s: s + pd.Timedelta(hours=24)]
        if len(seg) < 40:
            continue
        o = k.open.get(s, np.nan); mv = (seg / o - 1).abs().to_numpy()[:48]
        if len(moves) >= lookback:
            sig = np.nanmean(np.vstack([m[:48] for m in moves[-lookback:] if len(m) >= 48]), axis=0)
            pos = 0; pnl = 0.0; prev = o
            for i, cc in enumerate(seg.to_numpy()[:48]):
                pnl += pos * (cc / prev - 1); prev = cc
                up, dn = o * (1 + sig[i]), o * (1 - sig[i]); new = pos
                if pos == 0:
                    new = 1 if cc > up else (-1 if cc < dn else 0)
                elif pos == 1 and cc < up:
                    new = 0
                elif pos == -1 and cc > dn:
                    new = 0
                if new != pos:
                    pnl -= abs(new - pos) * cost / 1e4; pos = new
            pnl -= abs(pos) * cost / 1e4
            out[(s + pd.Timedelta(hours=1)).floor("D")] = pnl
        moves.append(mv)
    return pd.Series(out)


g12 = pd.concat([monday_trend("BTC"), monday_trend("ETH")], axis=1).fillna(0).mean(axis=1)
rep("G12 Monday-anchored intraday trend BTC+ETH", g12, "weekly, one session per week")
pd.DataFrame(T.ROWS).to_csv(ROOT / "results/gen61_crypto.csv", index=False)

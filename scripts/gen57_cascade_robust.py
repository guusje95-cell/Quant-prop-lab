"""Gen57 B4 robustness (pre-registered rule: 1h return < -3 sigma, OI -5%, volume > 95th pct -> long, stop low - 1 ATR, exit 12h; mirror).
Checks: event counts, per-year, 2x costs, one-hour entry delay, k = 2.5 / 3.5, long-only vs short-only, per-coin breadth,
worst days, behaviour on C*'s worst days. Writes results/gen57_cascade_robust.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_timing as T
from qpl.lab import binance_pack as B

C = B.coins()
CACHE = {}


def hourly(coin):
    if coin not in CACHE:
        h = B.k5(coin)
        df = pd.DataFrame({"c": h.close.resample("1h").last(), "lo": h.low.resample("1h").min(), "hi": h.high.resample("1h").max(),
                           "v": h.quote_volume.resample("1h").sum()})
        df["oi"] = B.metrics(coin)["sum_open_interest_value"].resample("1h").last().reindex(df.index)
        CACHE[coin] = df
    return CACHE[coin]


def cascade(coin, hold=12, k=3.0, cost=5, delay=0, sides=(1, -1)):
    d = hourly(coin); c, lo, hi, v, o = d.c, d.lo, d.hi, d.v, d.oi
    r = c.pct_change(); sd = r.rolling(720).std().shift(1); vq = v.rolling(720).quantile(0.95).shift(1); doi = o.pct_change()
    atr = (hi - lo).rolling(14).mean()
    ev = {1: (r < -k * sd) & (doi < -0.05) & (v > vq), -1: (r > k * sd) & (doi < -0.05) & (v > vq)}
    pnl = pd.Series(0.0, index=c.index); cv, lov, hiv, atv = c.to_numpy(), lo.to_numpy(), hi.to_numpy(), atr.to_numpy(); n = len(cv)
    trades = []
    for side in sides:
        for t in np.flatnonzero(ev[side].to_numpy()):
            e = t + delay
            if e + 1 >= n:
                continue
            entry = cv[e]; stop = (lov[t] - atv[t]) if side > 0 else (hiv[t] + atv[t])
            ex = None
            for j in range(e + 1, min(e + 1 + hold, n)):
                if (side > 0 and lov[j] <= stop) or (side < 0 and hiv[j] >= stop):
                    ex = (j, stop); break
            if ex is None:
                j = min(e + hold, n - 1); ex = (j, cv[j])
            ret = side * (ex[1] / entry - 1) - 2 * cost / 1e4
            pnl.iloc[ex[0]] += 0.2 * ret; trades.append((c.index[t], coin, side, ret))
    return pnl.groupby(pnl.index.floor("D")).sum(), trades


def portfolio(**kw):
    res = [cascade(c, **kw) for c in C]
    pnl = pd.concat([r[0] for r in res], axis=1).sum(axis=1).loc["2021-12-01":]
    tr = pd.DataFrame([t for r in res for t in r[1]], columns=["time", "coin", "side", "ret"])
    return pnl, tr


base, trades = portfolio()
print("events:", len(trades), "per year:", trades.groupby(trades.time.dt.year).size().to_dict())
print("mean trade by year:", trades.groupby(trades.time.dt.year).ret.mean().round(4).to_dict(), "hit rate:", round((trades.ret > 0).mean(), 3))
print("long vs short mean:", trades.groupby("side").ret.agg(["mean", "count"]).round(4).to_dict())
print("per-coin mean trade (2023+):", trades[trades.time >= "2023"].groupby("coin").ret.mean().round(4).sort_values().to_dict())
print("coins positive 2023+:", int((trades[trades.time >= "2023"].groupby("coin").ret.mean() > 0).sum()), "of", trades.coin.nunique())
print("worst days 2023+:", base.loc["2023":].nsmallest(5).round(4).to_dict())
T.report("B4 base (k3, 12h, 5bp)", base)
T.report("B4 2x costs (10bp/side)", portfolio(cost=10)[0])
T.report("B4 entry delayed 1 hour", portfolio(delay=1)[0])
T.report("B4 k=2.5", portfolio(k=2.5)[0])
T.report("B4 k=3.5", portfolio(k=3.5)[0])
T.report("B4 long (cascade buy) only", portfolio(sides=(1,))[0])
T.report("B4 short (squeeze fade) only", portfolio(sides=(-1,))[0])
pd.DataFrame(T.ROWS).to_csv(ROOT / "results/gen57_cascade_robust.csv", index=False)
trades.to_csv(ROOT / "results/gen57_cascade_trades.csv", index=False)

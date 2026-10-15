"""Gen64 (config/gen64_protocol.json): 4h trend ensemble, 12h trend, BTC->alt 5-min lead-lag. Writes results/gen64_crypto.csv and the
daily P&L of each candidate to results/cache_gen64_daily.parquet (for the portfolio check)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_timing as T
from qpl.lab import binance_pack as B

END = "2026-09-30 23:00"


def breakout_pos(c, h, l, n_in, n_out):
    hi_in, lo_in = h.rolling(n_in).max().shift(1).to_numpy(), l.rolling(n_in).min().shift(1).to_numpy()
    hi_out, lo_out = h.rolling(n_out).max().shift(1).to_numpy(), l.rolling(n_out).min().shift(1).to_numpy()
    cv = c.to_numpy(); pos = np.zeros(len(cv)); p = 0
    for i in range(len(cv)):
        if p == 0:
            p = 1 if cv[i] > hi_in[i] else (-1 if cv[i] < lo_in[i] else 0)
        elif p == 1 and cv[i] < lo_out[i]:
            p = 0
        elif p == -1 and cv[i] > hi_out[i]:
            p = 0
        pos[i] = p
    return pd.Series(pos, index=c.index)


def trend(coin, rule="4h", pairs=((20, 10),), cost=5):
    k = B.k5(coin); c = k.close.resample(rule).last().loc[:END]; h = k.high.resample(rule).max().loc[:END]; l = k.low.resample(rule).min().loc[:END]
    pos = sum(breakout_pos(c, h, l, a, b) for a, b in pairs) / len(pairs)
    bpd = int(pd.Timedelta("1D") / pd.Timedelta(rule))
    r = c.pct_change().fillna(0)
    lev = (0.10 / (r.rolling(bpd * 30).std().shift(1) * np.sqrt(bpd * 365))).clip(upper=2.0).fillna(0)
    held = (pos * lev).shift(1).fillna(0)
    f = B.funding(coin).reindex(c.index).fillna(0.0)
    pnl = held * r - held * f.shift(-1).fillna(0) - held.diff().abs().fillna(0) * cost / 1e4
    return pnl.groupby(pnl.index.floor("D")).sum()


ENS = ((10, 5), (20, 10), (40, 20))
res = {}
res["J1 4h trend ensemble BTC/ETH/SOL (PRIMARY)"] = pd.concat([trend(c, "4h", ENS) for c in ("BTC", "ETH", "SOL")], axis=1).fillna(0).mean(axis=1)
res["J1 4h trend ensemble, 6 coins"] = pd.concat([trend(c, "4h", ENS) for c in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE")], axis=1).fillna(0).mean(axis=1)
res["J2 12h trend 20/10 BTC/ETH/SOL"] = pd.concat([trend(c, "12h") for c in ("BTC", "ETH", "SOL")], axis=1).fillna(0).mean(axis=1)
res["ref I6 4h trend 20/10 BTC/ETH/SOL"] = pd.concat([trend(c, "4h") for c in ("BTC", "ETH", "SOL")], axis=1).fillna(0).mean(axis=1)


# J3 lead-lag
def leadlag(maker=False):
    btc = B.k5("BTC"); rb = btc.close.pct_change(); sd = rb.rolling(288 * 30).std().shift(1)
    trig = (rb.abs() > 2 * sd)
    out = []
    for coin in [c for c in B.coins() if c != "BTC"]:
        k = B.k5(coin).reindex(btc.index); ra = k.close.pct_change()
        side = np.sign(rb)
        lag = trig & (ra * side < 0.5 * rb.abs())
        entry = k.close.where(lag); exitp = k.close.shift(-3)
        gross = side * (exitp / entry - 1)
        if maker:
            nxt = k.shift(-1)
            f0 = np.where(side > 0, nxt.low <= k.close * (1 - 1e-4), nxt.high >= k.close * (1 + 1e-4))
            cost = pd.Series(np.where(f0, 2, 5), index=k.index) / 1e4 + 5 / 1e4
        else:
            cost = 10 / 1e4
        pnl = (0.05 * (gross - cost)).where(lag).fillna(0.0)
        out.append(pnl.groupby(pnl.index.floor("D")).sum())
    return pd.concat(out, axis=1).sum(axis=1).loc[:"2026-09-30"]


res["J3 BTC->alt lead-lag 5-min (taker)"] = leadlag(False)
res["J3 BTC->alt lead-lag 5-min (maker entry)"] = leadlag(True)
for n, x in res.items():
    T.report(n, x); T.ROWS[-1]["ret_2022"] = float((1 + x.loc["2022"]).prod() - 1)
pd.DataFrame(T.ROWS).to_csv(ROOT / "results/gen64_crypto.csv", index=False)
pd.DataFrame(res).to_parquet(ROOT / "results/cache_gen64_daily.parquet")

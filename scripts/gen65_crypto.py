"""Gen65 (config/gen65_protocol.json): own-history ranking, Friday expiry window, 6h trend with coin selection; plus the
portfolio check. Writes results/gen65_crypto.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_timing as T
import crypto_sleeves as CS
from qpl.lab import binance_pack as B

C = B.coins(); COST = 5 / 1e4
P = B.panel("close", "1D", C).loc[:"2026-09-30"]; R = P.pct_change(fill_method=None)
F = B.funding_panel(C); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D"); FD = F.groupby(level=0).sum().reindex(P.index)
listed = P.notna().cumsum() >= 60
weekly = pd.Series(np.arange(len(P)) % 7 == 0, index=P.index)
cands = {}


def pnl_w(w):
    held = w.reindex(P.index).fillna(0.0).shift(1).fillna(0.0)
    return (held * R.fillna(0) - held * FD.fillna(0)).sum(axis=1) - held.diff().abs().sum(axis=1) * COST


def terc(score):
    rk = score.where(listed).rank(axis=1, pct=True); lo, hi = rk <= 1 / 3, rk > 2 / 3
    w = hi.astype(float).div(hi.sum(axis=1), axis=0) - lo.astype(float).div(lo.sum(axis=1), axis=0)
    return w.fillna(0.0).where(weekly, np.nan).ffill().fillna(0.0)


# K1 own-history ranking
m30 = P / P.shift(30) - 1
z = (m30 - m30.rolling(365, min_periods=180).mean()) / m30.rolling(365, min_periods=180).std()
cands["K1 own-history z of 30d momentum, XS tercile (PRIMARY)"] = pnl_w(terc(z))
prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in C}).reindex(P.index).rolling(7).mean()
zp = (prem - prem.rolling(365, min_periods=180).mean()) / prem.rolling(365, min_periods=180).std()
cands["K1 variant: own-history z of premium (long low z)"] = pnl_w(terc(-zp))


# K2 Friday expiry window
def expiry(coin, which="last", maker=False):
    k = B.k5(coin); days = pd.date_range("2020-01-03", "2026-09-30", freq="W-FRI")
    if which == "last":
        days = days[(days + pd.Timedelta(days=7)).month != days.month]
    out = {}
    for d in days:
        t7, t8, t10 = d + pd.Timedelta(hours=7), d + pd.Timedelta(hours=8), d + pd.Timedelta(hours=10)
        if t7 not in k.index or t8 not in k.index or t10 not in k.index:
            continue
        o7, o8, o10 = k.open[t7], k.open[t8], k.open[t10]
        if maker:
            c7 = 2 if k.high[t7] >= o7 * (1 + 1e-4) else 5
            c8 = 2 if k.low[t8] <= o8 * (1 - 1e-4) else 5
            c10 = 2 if k.high[t10] >= o10 * (1 + 1e-4) else 5
            cost = (c7 + 2 * c8 + c10) / 1e4                      # close the short and open the long at 08:00 (two fills)
        else:
            cost = 4 * COST
        out[d] = -(o8 / o7 - 1) + (o10 / o8 - 1) - cost
    s = pd.Series(out)
    return s.reindex(P.index).fillna(0.0)


cands["K2 expiry window, last Friday, BTC+ETH (PRIMARY)"] = (expiry("BTC") + expiry("ETH")) / 2
cands["K2 variant: every Friday"] = (expiry("BTC", "all") + expiry("ETH", "all")) / 2
cands["K2 variant: last Friday, maker"] = (expiry("BTC", maker=True) + expiry("ETH", maker=True)) / 2


# K3 6h trend with ATR trailing stop and monthly coin selection
def trend6(coin):
    k = B.k5(coin); c = k.close.resample("6h").last().loc[:"2026-09-30 23:00"]; h = k.high.resample("6h").max().loc[c.index]; l = k.low.resample("6h").min().loc[c.index]
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1); atr = tr.rolling(14).mean()
    hi20, lo20 = h.rolling(20).max().shift(1), l.rolling(20).min().shift(1)
    cv, hv, lv, av, hi_, lo_ = c.to_numpy(), h.to_numpy(), l.to_numpy(), atr.to_numpy(), hi20.to_numpy(), lo20.to_numpy()
    pos = np.zeros(len(cv)); p = 0; best = np.nan
    for i in range(len(cv)):
        if p == 1:
            best = max(best, hv[i])
            if cv[i] < best - 3 * av[i]:
                p = 0
        elif p == -1:
            best = min(best, lv[i])
            if cv[i] > best + 3 * av[i]:
                p = 0
        if p == 0:
            if cv[i] > hi_[i]:
                p, best = 1, hv[i]
            elif cv[i] < lo_[i]:
                p, best = -1, lv[i]
        pos[i] = p
    pos = pd.Series(pos, index=c.index); r = c.pct_change().fillna(0)
    lev = (0.10 / (r.rolling(4 * 30).std().shift(1) * np.sqrt(4 * 365))).clip(upper=2.0).fillna(0)
    f = B.funding(coin).reindex(c.index).fillna(0.0)
    held_l = (pos.clip(lower=0) * lev * 0.7).shift(1).fillna(0); held_s = (pos.clip(upper=0) * lev * 0.3).shift(1).fillna(0)
    held = held_l + held_s
    pnl = held * r - held * f.shift(-1).fillna(0) - held.diff().abs().fillna(0) * COST
    return pnl.groupby(pnl.index.floor("D")).sum()


per = pd.DataFrame({c: trend6(c) for c in C}).reindex(P.index).fillna(0.0)
roll = per.rolling(90, min_periods=60).mean() / per.rolling(90, min_periods=60).std()
sel = roll.resample("MS").last().shift(1)                                   # chosen at the end of the previous month
sel = sel.rank(axis=1, ascending=False) <= 5
mask = sel.reindex(P.index, method="ffill").fillna(False)
cands["K3 6h trend, ATR stop, monthly top-5 coins, 70/30 (PRIMARY)"] = (per * mask).sum(axis=1) / 5

for n, x in cands.items():
    T.report(n, x); T.ROWS[-1]["ret_2022"] = float((1 + x.loc["2022"]).prod() - 1)

# portfolio check
H = CS.all_sleeves(); D = H.groupby(H.index.floor("D")).sum()[["C*", "premium carry", "cascade"]]
def port(df):
    z_ = df.loc["2022-01-01":"2026-09-30"].fillna(0.0); z_ = z_ / (z_.std() * np.sqrt(365)) * 0.10
    x = z_.mean(axis=1); x = x * 0.15 / (x.std() * np.sqrt(365)); m = (1 + x).resample("ME").prod() - 1; eq = (1 + x).cumprod()
    return round(x.mean() / x.std() * np.sqrt(365), 3), round((m > 0).mean(), 3), round((eq / eq.cummax() - 1).min(), 3)
print("current portfolio (Sharpe 2022-26, pos months, maxDD):", port(D))
for n, x in cands.items():
    print("+", n, port(pd.concat([D, x.rename("new")], axis=1)))
pd.DataFrame(T.ROWS).to_csv(ROOT / "results/gen65_crypto.csv", index=False)

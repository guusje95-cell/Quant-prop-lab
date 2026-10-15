"""Gen62 (config/gen62_protocol.json): market-neutral and bear-phase crypto sleeves. Writes results/gen62_crypto.csv."""
import itertools, sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_timing as T
import gen57_cascade_hourly as CH
from qpl.lab import binance_pack as B
from qpl.lab.strategies_papers import engle_granger

C = B.coins(); COST = 5 / 1e4
P = B.panel("close", "1D", C).loc[:"2026-09-30"]; R = P.pct_change(fill_method=None)
F = B.funding_panel(C); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D"); FD = F.groupby(level=0).sum().reindex(P.index)
listed = P.notna().cumsum() >= 60


def pnl_from_weights(w):
    held = w.reindex(P.index).fillna(0.0).shift(1).fillna(0.0)
    return (held * R.fillna(0) - held * FD.fillna(0)).sum(axis=1) - held.diff().abs().sum(axis=1) * COST


def rep(name, x, note=""):
    T.report(name, x, note)
    r = T.ROWS[-1]; r["ret_2022"] = float((1 + x.loc["2022"]).prod() - 1)
    r["sharpe_2023plus"] = r.get("2023+_sharpe", np.nan)


# ---------------- H1 pairs
def pairs(F_days=180, Z=2.0, npairs=5, notional=0.2):
    lp = np.log(P)
    w = pd.DataFrame(0.0, index=P.index, columns=C)
    months = pd.date_range("2020-07-01", "2026-09-01", freq="MS")
    for m in months:
        hist = lp.loc[m - pd.Timedelta(days=F_days): m - pd.Timedelta(days=1)]
        hist = hist.loc[:, hist.notna().all() & listed.reindex([m - pd.Timedelta(days=1)]).iloc[0].reindex(hist.columns).fillna(False)]
        cand = []
        for a, b in itertools.combinations(hist.columns, 2):
            y, x = hist[a].to_numpy(), hist[b].to_numpy()
            if np.corrcoef(y, x)[0, 1] < 0.8:
                continue
            beta, alpha = np.polyfit(x, y, 1); e = y - beta * x - alpha
            lam = np.polyfit(e[:-1], np.diff(e), 1)[0]
            if lam >= 0:
                continue
            hl = -np.log(2) / lam
            if not 2 <= hl <= 30:
                continue
            if engle_granger(y, x) < 0.05:
                cand.append((hl, a, b, beta, alpha, e.mean(), e.std()))
        cand.sort()
        days = P.loc[m: m + pd.offsets.MonthEnd(0)].index
        for hl, a, b, beta, alpha, mu, sd in cand[:npairs]:
            pos, stopped = 0, False
            for d in days[:-1]:                                   # flat on the last day of the month
                if np.isnan(lp.at[d, a]) or np.isnan(lp.at[d, b]):
                    continue
                z = (lp.at[d, a] - beta * lp.at[d, b] - alpha - mu) / sd
                if pos == 0 and not stopped and abs(z) > Z:
                    pos = -1 if z > 0 else 1
                elif pos != 0 and (abs(z) < 0.5 or abs(z) > 4):
                    stopped = abs(z) > 4; pos = 0
                if pos:
                    w.at[d, a] += pos * notional; w.at[d, b] -= pos * notional
    return pnl_from_weights(w)


for Fd, Z in itertools.product((180, 90), (2.0, 1.5, 2.5)):
    rep(f"H1 pairs F={Fd} Z={Z}" + (" (PRIMARY)" if (Fd, Z) == (180, 2.0) else ""), pairs(Fd, Z))


# ---------------- H2 premium variants (baseline G4)
prem_d = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in C}).reindex(P.index)
fund7 = F.groupby(level=0).sum().reindex(P.index).rolling(7).mean()


def tercile_ls(score, hold=7, invvol=False):
    rk = score.where(listed).rank(axis=1, pct=True)
    lo, hi = (rk <= 1 / 3), (rk > 2 / 3)
    if invvol:
        iv = 1 / (R.rolling(30).std())
        wl = (iv.where(lo)).div(iv.where(lo).sum(axis=1), axis=0); ws = (iv.where(hi)).div(iv.where(hi).sum(axis=1), axis=0)
        w = wl.fillna(0) - ws.fillna(0)
    else:
        w = lo.astype(float).div(lo.sum(axis=1), axis=0) - hi.astype(float).div(hi.sum(axis=1), axis=0)
    w = w.fillna(0.0).where(pd.Series(np.arange(len(w)) % hold == 0, index=w.index), np.nan).ffill().fillna(0.0)
    return pnl_from_weights(w)


g4 = tercile_ls(prem_d.rolling(7).mean()); rep("H2 baseline G4 premium carry", g4)
rep("H2a residual premium (7d minus 60d)", tercile_ls(prem_d.rolling(7).mean() - prem_d.rolling(60).mean()))
rk_p = prem_d.rolling(7).mean().where(listed).rank(axis=1, pct=True); rk_f = fund7.where(listed).rank(axis=1, pct=True)
rep("H2b combined premium + funding rank", tercile_ls((rk_p + rk_f) / 2))
rep("H2c G4 with inverse-vol legs", tercile_ls(prem_d.rolling(7).mean(), invvol=True))


# ---------------- H3 bear-phase short sleeve
btc_bear = P["BTC"] < P["BTC"].rolling(200).mean()
def bear_sleeve(M=50, L=20, target=0.10):
    cond = (P < P.rolling(M).mean()) & (P / P.shift(L) - 1 < 0) & listed
    cond = cond.mul(btc_bear, axis=0)
    iv = 1 / R.rolling(30).std()
    w = -(iv.where(cond)).div(iv.where(cond).sum(axis=1), axis=0).fillna(0.0)
    raw = pnl_from_weights(w)
    port_vol = raw.rolling(60).std().shift(1) * np.sqrt(365)
    k = (target / port_vol).clip(upper=3.0).fillna(1.0)
    return pnl_from_weights(w.mul(k, axis=0))


for M, L in itertools.product((50, 100), (20, 60)):
    x = bear_sleeve(M, L)
    rep(f"H3 bear short sleeve M={M} L={L}" + (" (PRIMARY)" if (M, L) == (50, 20) else ""), x)
print("H3 share of days active:", round(float(btc_bear.loc["2020-07":].mean()), 2))


# ---------------- H4 cascade with BTC > 200d MA regime
bull = (P["BTC"] > P["BTC"].rolling(200).mean()).shift(1).fillna(False)
def cascade_regime(K=3, H=12, k=3.0, size=0.2):
    trades = []
    for coin in C:
        d = CH.hourly(coin).loc[:"2026-09-30 23:00"]; c, lo, hi, v, o = d.c, d.lo, d.hi, d.v, d.oi
        r = c.pct_change(); sd = r.rolling(720).std().shift(1); vq = v.rolling(720).quantile(0.95).shift(1); doi = o.pct_change()
        atr = (hi - lo).rolling(14).mean(); ev = (r < -k * sd) & (doi < -0.05) & (v > vq)
        cv, lov, atv = c.to_numpy(), lo.to_numpy(), atr.to_numpy(); n = len(cv)
        for t in np.flatnonzero(ev.to_numpy()):
            if t + 1 >= n or not bool(bull.get(c.index[t].floor("D"), False)):
                continue
            stop = lov[t] - atv[t]; ex = None
            for j in range(t + 1, min(t + 1 + H, n)):
                if lov[j] <= stop:
                    ex = (j, stop); break
            if ex is None:
                ex = (min(t + H, n - 1), cv[min(t + H, n - 1)])
            trades.append((c.index[t], coin, c.index[ex[0]], ex[1] / cv[t] - 1 - 2 * COST))
    trades.sort(key=lambda x: (x[0], x[1])); open_ex = []; pnl = {}           # ties broken by coin name, never by outcome
    for t0, _, t1, ret in trades:
        open_ex = [e for e in open_ex if e > t0]
        if len(open_ex) >= K:
            continue
        open_ex.append(t1); dd = t1.floor("D"); pnl[dd] = pnl.get(dd, 0.0) + size * ret
    return pd.Series(pnl).sort_index().reindex(pd.date_range("2021-12-01", "2026-09-30")).fillna(0.0)


for K, H in itertools.product((3, 5), (12, 24)):
    rep(f"H4 cascade, BTC>200d regime, K={K} H={H}" + (" (PRIMARY)" if (K, H) == (3, 12) else ""), cascade_regime(K, H), "OI from 2021-12; DEV = 2022 only")

pd.DataFrame(T.ROWS).to_csv(ROOT / "results/gen62_crypto.csv", index=False)

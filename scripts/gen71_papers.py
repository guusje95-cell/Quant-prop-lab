"""Gen71 (config/gen71_protocol.json): uploaded papers 6-9.
Z  Zarattini et al. Donchian ensemble | G  Guo et al. cross-crypto predictability | S  Borri et al. CMOM.
Writes results/gen71_papers.csv and results/cache_gen71_daily.parquet."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_timing as T
import crypto_sleeves as CS
from qpl.lab import binance_pack as B

warnings.filterwarnings("ignore")
C = B.coins(); END = "2026-09-30"
P = B.panel("close", "1D", C).loc[:END]; R = P.pct_change(fill_method=None)
QV = B.panel("quote_volume", "1D", C).loc[:END]
F = B.funding_panel(C); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D"); FD = F.groupby(level=0).sum().reindex(P.index)
listed = P.notna().cumsum() >= 60
cands = {}


def pnl_w(w, cost=5):
    held = w.reindex(P.index).ffill().fillna(0.0).shift(1).fillna(0.0)
    return (held * R.fillna(0) - held * FD.fillna(0)).sum(axis=1) - held.diff().abs().sum(axis=1) * cost / 1e4


# ---------------------------------------------------------------- Z: Zarattini, Pagani & Barbon Donchian ensemble
LOOKS = (5, 10, 20, 30, 60, 90, 150, 250, 360)


def donchian_pos(c, n, longshort):
    up, dn = c.rolling(n).max().to_numpy(), c.rolling(n).min().to_numpy(); mid = 0.5 * (up + dn); cv = c.to_numpy()
    pos = np.zeros(len(cv)); p = 0; stop = np.nan
    for i in range(len(cv)):
        if not np.isfinite(up[i]):
            continue
        if p == 1 and cv[i] <= stop:
            p = 0
        elif p == -1 and cv[i] >= stop:
            p = 0
        if cv[i] >= up[i]:
            if p != 1:
                stop = mid[i]
            p = 1
        elif longshort and cv[i] <= dn[i]:
            if p != -1:
                stop = mid[i]
            p = -1
        if p == 1:
            stop = max(stop, mid[i])                              # stop used tomorrow
        elif p == -1:
            stop = min(stop, mid[i])
        pos[i] = p
    return pos


def combo(coin, longshort=False):
    c = P[coin].dropna()
    sig = np.mean([donchian_pos(c, n, longshort) for n in LOOKS], axis=0)
    vol = c.pct_change().rolling(90).std().to_numpy() * np.sqrt(365)
    lev = np.minimum(0.25 / vol, 2.0)
    target = np.nan_to_num(sig * lev)
    held = np.zeros(len(target)); h = 0.0
    for i in range(len(target)):
        sig_changed = i > 0 and sig[i] != sig[i - 1]
        if sig_changed or (target[i] == 0) != (h == 0) or abs(target[i] - h) > 0.2 * abs(h):
            h = target[i]
        held[i] = h
    return pd.Series(held, index=c.index)


def zarattini(coins, longshort=False):
    W = pd.DataFrame({c: combo(c, longshort) for c in coins}).reindex(P.index)
    elig = (P[coins].notna().cumsum() >= 365)
    nB = elig.sum(axis=1).resample("MS").first().reindex(P.index, method="ffill")   # B fixed at the start of each month
    return W.where(elig, 0.0).fillna(0.0).div(nB.replace(0, np.nan), axis=0).fillna(0.0)


z1w = zarattini(C)
cands["Z1 Zarattini Donchian combo, long-only, 20 coins (PRIMARY)"] = pnl_w(z1w)
cands["Z2 Zarattini combo, long-short"] = pnl_w(zarattini(C, True))
zb = pd.DataFrame({"BTC": combo("BTC")}).reindex(P.index).fillna(0.0).where(P[["BTC"]].notna().cumsum() >= 365, 0.0)
cands["Z3 Zarattini combo, BTC only"] = pnl_w(zb)
print("Z1 mean gross exposure:", round(z1w.abs().sum(axis=1).loc["2021":].mean(), 2), flush=True)


# ---------------------------------------------------------------- G: Guo, Sang, Tu & Wang cross-crypto predictability
def g_pnl(Rb, fc, cost=4):
    """Rb: bar returns (t), fc: forecast of the next bar made at the close of bar t. Equal-weight quintile long-short."""
    s = fc.where(Rb.notna()); n = (s.notna().sum(axis=1) * 0.2).round().clip(lower=1)
    hi = s.rank(axis=1, ascending=False, method="first").le(n, axis=0); lo = s.rank(axis=1, method="first").le(n, axis=0)
    w = hi.astype(float).div(n, axis=0) - lo.astype(float).div(n, axis=0)
    w = w.where(s.notna().sum(axis=1) >= 10, 0.0).fillna(0.0)
    pnl = (w.shift(1) * Rb.fillna(0)).sum(axis=1) - w.diff().abs().sum(axis=1) * cost / 1e4
    return pnl.groupby(pnl.index.floor("D")).sum().reindex(P.index).fillna(0.0)


def btc_univariate(Rb, win=720):
    x = Rb["BTC"]; others = [c for c in C if c != "BTC"]
    day0 = Rb.index.floor("D"); first = ~day0.duplicated()                 # first bar of each day: estimate with bars before it
    fc = {}
    for c in others:
        y = Rb[c]; xs = x.shift(1)                                         # y_{t} on x_{t-1}
        cov = y.rolling(win, min_periods=win).cov(xs); var = xs.rolling(win, min_periods=win).var()
        b = (cov / var).shift(1); a = (y.rolling(win).mean() - (cov / var) * xs.rolling(win).mean()).shift(1)
        b = b.where(first).ffill(); a = a.where(first).ffill()
        fc[c] = a + b * x                                                  # forecast of y_{t+1} from x_t
    return pd.DataFrame(fc)


R5 = B.panel("close", "5min", C).loc[:END + " 23:55"].pct_change(fill_method=None)
print("5m panel", R5.shape, flush=True)
cands["G1 Guo BTC-lead quintile, 5m, every bar (PRIMARY)"] = g_pnl(R5[[c for c in C if c != "BTC"]], btc_univariate(R5))
gross = g_pnl(R5[[c for c in C if c != "BTC"]], btc_univariate(R5), cost=0)
print("G1 gross Sharpe 2020-26:", round(gross.mean() / gross.std() * np.sqrt(365), 2), "gross mean/day bp:", round(gross.mean() * 1e4, 1), flush=True)


def adaptive_lasso(Rb, win=720):
    from sklearn.linear_model import LassoLarsIC
    days = Rb.index.floor("D").unique(); fc = pd.DataFrame(np.nan, index=Rb.index, columns=C)
    Xall = Rb.to_numpy(); pos_of = {t: i for i, t in enumerate(Rb.index)}
    for d in days:
        i0 = pos_of.get(d)
        if i0 is None or i0 < win + 1:
            continue
        i1 = pos_of.get(d + pd.Timedelta(days=1), len(Rb))
        blk = Xall[i0 - win - 1:i0]; ok_cols = np.isfinite(blk).all(axis=0)
        if ok_cols.sum() < 10:
            continue
        X = blk[:-1][:, ok_cols]; Y = blk[1:][:, ok_cols]
        mu, sd = X.mean(axis=0), X.std(axis=0); sd[sd == 0] = 1; Xs = (X - mu) / sd
        Xnow = (Xall[i0 - 1:i1 - 1][:, ok_cols] - mu) / sd                  # x_t for forecasting bars i0..i1-1
        cols = np.array(C)[ok_cols]
        for k, c in enumerate(cols):
            y = Y[:, k]
            ols = np.linalg.lstsq(np.c_[np.ones(len(y)), Xs], y, rcond=None)[0][1:]
            wgt = np.abs(ols) + 1e-12
            m = LassoLarsIC(criterion="bic").fit(Xs * wgt, y)
            beta = m.coef_ * wgt
            f = m.intercept_ + np.nan_to_num(Xnow) @ beta
            fc.iloc[i0:i1, list(C).index(c)] = f
    return fc


g2fc = adaptive_lasso(R5)
cands["G2 Guo adaptive LASSO quintile, 5m"] = g_pnl(R5, g2fc)
R1h = B.panel("close", "1h", C).loc[:END + " 23:00"].pct_change(fill_method=None)
cands["G3 Guo BTC-lead quintile, 1h"] = g_pnl(R1h[[c for c in C if c != "BTC"]], btc_univariate(R1h))
del R5


# ---------------------------------------------------------------- S: Borri et al. CMOM
SUN = P.index[P.index.dayofweek == 6]
mom2 = (P / P.shift(14) - 1).reindex(SUN).where(listed.reindex(SUN))
wv = QV.rolling(30, min_periods=20).mean().reindex(SUN)
nq = (mom2.notna().sum(axis=1) * 0.2).round().clip(lower=1)
hi = mom2.rank(axis=1, ascending=False, method="first").le(nq, axis=0); lo = mom2.rank(axis=1, method="first").le(nq, axis=0)
ws = (wv * hi).div((wv * hi).sum(axis=1), axis=0).fillna(0) - (wv * lo).div((wv * lo).sum(axis=1), axis=0).fillna(0)
ws = ws.where(mom2.notna().sum(axis=1) >= 10, 0.0)
cands["S1 Borri et al. CMOM 2-week momentum quintile (PRIMARY)"] = pnl_w(ws.reindex(P.index).ffill().fillna(0.0))

pd.DataFrame(cands).to_parquet(ROOT / "results/cache_gen71_daily.parquet")
for n, x in cands.items():
    T.report(n, x); T.ROWS[-1]["ret_2022"] = float((1 + x.loc["2022"]).prod() - 1)


def port(df):
    z = df.loc["2021-12-01":END].fillna(0.0); z = z / (z.std() * np.sqrt(365)) * 0.10
    x = z.mean(axis=1); x = x * 0.15 / (x.loc["2022":].std() * np.sqrt(365))
    x = (x * (0.15 / (x.rolling(30).std().shift(1) * np.sqrt(365))).clip(upper=1.5)).loc["2022-01-01":].dropna()
    x = x * 0.15 / (x.std() * np.sqrt(365)); m = (1 + x).resample("ME").prod() - 1; eq = (1 + x).cumprod()
    return round(x.mean() / x.std() * np.sqrt(365), 3), round((m > 0).mean(), 3), round((eq / eq.cummax() - 1).min(), 3)


H = CS.all_sleeves(); D = H.groupby(H.index.floor("D")).sum()[["C*", "premium carry", "cascade limit strict", "trend 4h"]]
base = port(D); print("v4 (daily recipe):", base)
for r in T.ROWS:
    x = cands[r["strategy"]]
    r["corr_v4"] = float(pd.concat([x, D.mean(axis=1)], axis=1).loc["2022":END].corr().iloc[0, 1])
    r["v4_plus"] = port(pd.concat([D, x.rename("new")], axis=1))[0]; r["v4_base"] = base[0]
    print("+", r["strategy"], r["v4_plus"], flush=True)
z1 = cands["Z1 Zarattini Donchian combo, long-only, 20 coins (PRIMARY)"]
rep = port(pd.concat([D.drop(columns="C*"), z1.rename("Z1")], axis=1))
print("replacement test, v4 with Z1 instead of C*:", rep, flush=True)
T.ROWS.append({"strategy": "Z1 replacing C* in v4", "v4_plus": rep[0], "v4_base": base[0]})
cs_ = D["C*"]
for k, (a, b) in T.PER.items():
    y = cs_.loc[a:b]
    if len(y) > 60:
        T.ROWS[-1][f"{k}_sharpe_cstar"] = float(y.mean() / y.std() * np.sqrt(365))
pd.DataFrame(T.ROWS).to_csv(ROOT / "results/gen71_papers.csv", index=False)

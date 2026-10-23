"""Shared data and sleeves for the orthogonal 'stress book' (config/gen359_program.json). Bybit-cost accounting throughout.
    import stressbook as SB; h = SB.premium_spike(side=1, maker=True); SB.evaluate({"name": h})"""
import json
import sys
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B, extra_pack as X
END = "2026-09-30"
coins = CS._breadth_universe(); pk = B.coins()
Hc = CS._breadth_close(coins).loc[:END + " 23:00"]; idx = Hc.index; n = len(idx)
R = Hc.pct_change(fill_method=None).fillna(0.0)
_f = pd.concat([B.funding_panel(pk)] + [X.funding(c).rename(c) for c in coins if c not in pk], axis=1).sort_index()[coins]
FUND_RAW = _f.copy()
fund = _f.copy(); fund.index = fund.index - pd.Timedelta(hours=1); fund = fund.groupby(level=0).sum().reindex(idx).fillna(0.0)
_by = pd.read_csv(ROOT / "research_data/bybit/instruments.csv"); SYM = dict(zip(_by.coin, _by.symbol))
_spr = pd.read_csv(ROOT / "research_data/bybit/spreads.csv").set_index("symbol")["spread_bp_median"]
BCOST = pd.Series({c: 5.5 + 0.5 * float(_spr.get(SYM.get(c, ""), _spr.median())) for c in coins})       # bp per side
FB = fund.copy(); BYB_RAW = {}
for c in coins:
    f = ROOT / f"research_data/bybit/funding/{SYM.get(c, '')}.parquet"
    if c in SYM and f.exists():
        x = pd.read_parquet(f)["funding_rate"]; x.index = pd.DatetimeIndex(x.index); x = x[~x.index.duplicated()]; BYB_RAW[c] = x
        y = x.copy(); y.index = y.index - pd.Timedelta(hours=1); y = y.groupby(level=0).sum()
        FB.loc[y.index.min():, c] = y.reindex(idx).loc[y.index.min():].fillna(0.0)


def _rd(f):
    x = pd.read_parquet(f); x.index = pd.DatetimeIndex(x.index); return x[~x.index.duplicated()].sort_index()


@lru_cache(maxsize=1)
def lohi():
    LO = pd.concat([B.panel("low", "1h", pk)] + [_rd(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["low"].rename(c) for c in coins if c not in pk], axis=1)
    HI = pd.concat([B.panel("high", "1h", pk)] + [_rd(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["high"].rename(c) for c in coins if c not in pk], axis=1)
    for D in (LO, HI):
        D.index = pd.DatetimeIndex(D.index)
    return LO[~LO.index.duplicated()].reindex(idx)[coins], HI[~HI.index.duplicated()].reindex(idx)[coins]


def zz(g, w=720):
    return ((g - g.rolling(w, min_periods=int(w * 0.7)).mean().shift(1)) / g.rolling(w, min_periods=int(w * 0.7)).std().shift(1))


def pnl(P, maker=False, fin=None):
    """Hourly P&L of hourly positions P (fraction of equity per coin). Bybit taker cost per coin; maker=True: each change is a limit order
    at the previous close, filled on a 2 bp trade-through (2 bp fee), else market at the hour's close one hour late (Gen337 rule)."""
    fin = FB if fin is None else fin; dE = P.diff().fillna(P)
    if not maker:
        return (P * R).sum(axis=1) - (P * fin).sum(axis=1) - (dE.abs() * BCOST).sum(axis=1) / 1e4
    LO, HI = lohi(); prev = Hc.shift(1)
    filled = (((dE > 0) & (LO <= prev * (1 - 2e-4))) | ((dE < 0) & (HI >= prev * (1 + 2e-4)))).astype(float)
    Ee = P - dE * (1 - filled)
    return (Ee * R).sum(axis=1) - (Ee * fin).sum(axis=1) - (dE.abs() * (filled * 2.0 + (1 - filled) * BCOST)).sum(axis=1) / 1e4


@lru_cache(maxsize=1)
def premium_z():
    Z = {}
    for c in coins:
        p = (B.premium(c)["close"] if c in pk else X.premium(c)); p = p[~p.index.duplicated()]; p.index = pd.DatetimeIndex(p.index)
        Z[c] = zz(p.reindex(idx))
    return pd.DataFrame(Z, index=idx)


def spike_positions(Z, th=3.0, hold=4, side=0, size=0.1, max_open=None):
    P = np.zeros((n, len(coins))); A = Z.reindex(columns=coins).to_numpy()
    for j in range(len(coins)):
        z = np.nan_to_num(A[:, j])
        for t in np.flatnonzero(np.abs(z) > th):
            s = -np.sign(z[t])
            if side and s != side:
                continue
            P[t + 1:min(t + 1 + hold, n), j] = size * s
    return pd.DataFrame(P, index=idx, columns=coins)


def premium_spike(side=0, maker=False, th=3.0, hold=4):
    return pnl(spike_positions(premium_z(), th, hold, side), maker=maker)


D = Hc.resample("1D").last(); DR = D.pct_change(fill_method=None)


def daily_event_positions(mask, sign, hold=3, size=0.1, max_open=8):
    ev = []
    for j, c in enumerate(coins):
        for d in mask.index[mask[c].fillna(False).to_numpy()]:
            ev.append((d, j, float(sign.loc[d, c]) if isinstance(sign, pd.DataFrame) else float(sign)))
    ev.sort(); Pd = np.zeros((len(D), len(coins))); ends = []; di = {d: i for i, d in enumerate(D.index)}
    for d, j, s in ev:
        i = di[d]; ends = [e for e in ends if e > i]
        if len(ends) >= max_open or s == 0:
            continue
        Pd[i:i + hold, j] = size * s; ends.append(i + hold)
    w = pd.DataFrame(Pd, index=D.index, columns=coins)
    return w.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)


def crash_reversal(k=3.0, hold=3, filt=None, maker=False):
    sdd = DR.rolling(90, min_periods=60).std().shift(1); mask = DR < -k * sdd
    if filt is not None:
        mask = mask & filt.reindex(D.index).fillna(False).to_numpy()[:, None]
    return pnl(daily_event_positions(mask, 1.0, hold), maker=maker)


def negative_funding(th=-0.001, hold=24, maker=False):
    ev = []
    for j, c in enumerate(coins):
        f = FUND_RAW[c].dropna()
        for ts in f.index[f < th]:
            t = idx.get_indexer([ts.floor("h")])[0]
            if t >= 0:
                ev.append((t, j))
    ev.sort(); P = np.zeros((n, len(coins))); ends = []
    for t, j in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 5:
            continue
        P[t:min(t + hold, n), j] = 0.1; ends.append(t + hold)
    return pnl(pd.DataFrame(P, index=idx, columns=coins), maker=maker)


def daily(h):
    return h.groupby(h.index.floor("D")).sum().loc["2020-01-01":END]


def sh(d, a, z):
    x = d.loc[a:z]; return float(x.mean() / x.std() * np.sqrt(365)) if x.std() > 0 else np.nan


def periods(d):
    return [round(sh(d, "2020", "2022"), 3), round(sh(d, "2023", "2024"), 3), round(sh(d, "2025", END), 3)]


@lru_cache(maxsize=1)
def v86_daily():
    v = pd.read_parquet(ROOT / "results/cache_v86_final.parquet")["portfolio"]; return v.groupby(v.index.floor("D")).sum()


def build(sleeves, voltarget=False):
    """Equal risk by 2020-24 daily sd; optional 30-day vol targeting (15%, cap 2, lagged). Returns the daily book (15% vol on 2020-24)."""
    Dd = pd.DataFrame({k: daily(v) for k, v in sleeves.items()}).fillna(0.0)
    bk = (Dd / Dd.loc[:"2024"].std()).sum(axis=1)
    if voltarget:
        m = (0.15 / (bk.rolling(30).std() * np.sqrt(365))).clip(upper=2.0).shift(1); bk = bk * m.fillna(0.0)
    return bk * 0.15 / (bk.loc[:"2024"].std() * np.sqrt(365))


def evaluate(bk):
    full = sh(bk, "2020-01-01", END)
    return {"Sharpe 2020-22 / 2023-24 / 2025-26": periods(bk), "Sharpe 2020-24 (decisions)": round(sh(bk, "2020", "2024"), 3),
            "Sharpe 2020-26": round(full, 3), "EXPECTED LIVE (0.6 x 2020-26)": round(0.6 * full, 3),
            "corr v8.6 2022-26": round(float(pd.concat([bk, v86_daily()], axis=1).loc["2022":END].corr().iloc[0, 1]), 3),
            "by year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in bk.groupby(bk.index.year)}}

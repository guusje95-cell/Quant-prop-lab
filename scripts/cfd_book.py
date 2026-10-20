"""CFD book for BrightFunded 2-Step Classic swap-free (research/FIRM_COMPARISON_2026-10.md, Gen104), live-capable:
C* (swap-aware), premium carry (CFD coins), trend 4h, Weiss expiry, deleveraging bounce, Coinbase premium; P1 equal risk with
30-day vol targeting; BrightFunded costs (commission 0.012% per side, spread BTC 0.4 / ETH 2.7 / altcoins 10 bp, swap-free);
gross exposure capped at the 1:5 crypto leverage. Uses only data known at each hour (binance_pack cutoff + Coinbase candles
complete before the cutoff)."""
import os
from pathlib import Path

import numpy as np
import pandas as pd

import crypto_sleeves as CS
from qpl.lab import binance_pack as B

ROOT = Path(__file__).resolve().parents[1]
CFD = ["BTC", "ETH", "LTC", "XRP", "ADA", "DOGE", "SOL", "DOT", "AVAX", "LINK", "BCH"]
CFD_BASE = list(CFD)                                       # every sleeve except premium carry trades only these
BREADTH = os.environ.get("QPL_BREADTH") == "1"             # bf-b shadow book (Gen121): premium carry on all BrightFunded-listed coins
if BREADTH:
    from qpl.lab.extra_pack import BF_NEW
    CFD = CFD + BF_NEW
SPREAD = pd.Series({c: (0.4 if c == "BTC" else 2.7 if c == "ETH" else 10.0) for c in CFD})
COMM = 1.2
LEVERAGE_CAP = 5.0


def coinbase(product):
    """Coinbase hourly closes: research copy + live overlay, cut at QPL_CUTOFF (a candle counts once its hour is over)."""
    frames = [pd.read_parquet(ROOT / f"research_data/coinbase/{product}_1h.parquet")]
    live = os.environ.get("QPL_LIVE_PACK")
    if live and (Path(live) / "coinbase" / f"{product}_1h.parquet").exists():
        frames.append(pd.read_parquet(Path(live) / "coinbase" / f"{product}_1h.parquet"))
    d = pd.concat(frames); d = d[~d.index.duplicated(keep="last")].sort_index()["close"]
    cut = os.environ.get("QPL_CUTOFF")
    if cut:
        d = d[d.index + pd.Timedelta(hours=1) <= pd.Timestamp(cut)]
    return d


def hourly_returns(end):
    H1 = (CS._breadth_close(CFD) if BREADTH else B.panel("close", "1h", CFD)).loc[:end]
    return H1.pct_change(fill_method=None).fillna(0.0)


def d2h(w, idx):
    """daily weights (row d decided at the close of d) -> hourly positions held during day d+1 (extended one day for the next hour)"""
    w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)])))
    return w.reindex(columns=CFD).shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)


def cstar_w():
    cw = CS.cstar_weights().copy()
    a = cw.abs(); m = a.where(a > 0).mean(axis=1)
    return cw.where(a.ge(m * 0.5, axis=0), 0.0).reindex(columns=CFD_BASE).reindex(columns=CFD).fillna(0.0)


def premium_carry_w(look=7, hold=7):
    if BREADTH:
        return CS.premium_breadth_weights(CFD, look, hold).reindex(columns=CFD).fillna(0.0)
    P = B.panel("close", "1D", CFD)
    prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in CFD}).reindex(P.index).rolling(look).mean()
    listed = P.notna().cumsum() >= 60
    rk = (-prem).where(listed).rank(axis=1, pct=True)
    w = (rk > 2 / 3).astype(float).div((rk > 2 / 3).sum(axis=1), axis=0) - (rk <= 1 / 3).astype(float).div((rk <= 1 / 3).sum(axis=1), axis=0)
    return w.where(pd.Series(np.arange(len(w)) % hold == 0, index=w.index), np.nan).ffill().fillna(0.0)


def coinbase_premium_w(end):
    out = {}
    for c in ("BTC", "ETH"):
        cb = coinbase(f"{c}-USD"); bn = B.k5(c).close.resample("1h").last()
        prem = (cb / bn - 1).dropna().loc[:end]
        p24 = prem.rolling(24, min_periods=20).mean()
        z = (p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()
        zd = z.resample("1D").last()
        last_hour = prem.index.max()
        if pd.notna(last_hour) and last_hour.hour != 23:                       # today's daily value is not final yet
            zd = zd.loc[:last_hour.floor("D") - pd.Timedelta(days=1)]
        out[c] = pd.Series(np.where(zd > 1, 0.5, np.where(zd < -1, -0.5, 0.0)), index=zd.index)
    return pd.DataFrame(out).reindex(columns=CFD).fillna(0.0)


def positions():
    """Hourly position frames per sleeve (index: hours up to END + 1, columns CFD)."""
    END = pd.Timestamp(CS.END)
    R = hourly_returns(END)
    idx = R.index.append(pd.DatetimeIndex([R.index[-1] + pd.Timedelta(hours=1)]))
    daily = {"C*": cstar_w(), "premium carry": premium_carry_w(), "delev bounce": CS.delev_bounce_weights().reindex(columns=CFD).fillna(0.0),
             "coinbase premium": coinbase_premium_w(END)}
    pos = {k: d2h(w, idx) for k, w in daily.items()}
    _, tp = CS.trend4h(positions=True); pos["trend 4h"] = tp.reindex(index=idx, columns=CFD).fillna(0.0)
    _, wp = CS.weiss_expiry(positions=True); pos["Weiss expiry"] = wp.reindex(index=idx, columns=CFD).fillna(0.0)
    return R, pos, daily


def sleeve_pnl(pos, R):
    p = pos.reindex(R.index).fillna(0.0)
    turn = p.diff().abs().fillna(p.abs()).mul((SPREAD + COMM) / 1e4, axis=1).sum(axis=1)
    return (p * R).sum(axis=1) - turn                                           # swap-free account: no swap


SLEEVES = ["C*", "premium carry", "trend 4h", "Weiss expiry", "delev bounce", "coinbase premium"]

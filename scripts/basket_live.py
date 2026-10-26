"""v9.5 extra sleeves for paper trading (point-in-time: honours QPL_CUTOFF and the QPL_LIVE_PACK overlays).

  - diversifier basket (Gen391): 8 BTC/ETH signals, equal risk on 2022-24
  - relative crowding 6 (Gen397 / Gen404): market-neutral, BTC ETH SOL XRP BNB DOGE, mean of daily / 3-day / 8-hourly versions
  - trend 4h and alt kimchi neighbourhood ensembles (Gen383)

Every daily weight frame follows the book convention: row d is decided at the close of day d and held during day d + 1.
basket_weights() / rc_weights() also return the per-coin positions the paper's next-hour book needs."""
from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

import crypto_sleeves as CS
from qpl.lab import binance_pack as B

ROOT = Path(__file__).resolve().parents[1]
LIVE = Path(os.environ["QPL_LIVE_PACK"]) if os.environ.get("QPL_LIVE_PACK") else None
CUT = pd.Timestamp(os.environ["QPL_CUTOFF"]) if os.environ.get("QPL_CUTOFF") else None
END = CS.END
DAYS = pd.date_range("2019-06-01", pd.Timestamp(END).normalize())
ND = ROOT / "research_data/newdata"
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE")
MEMBERS = ["Gen249 A USDT premium", "mint shock", "Gen120 D2 call-minus-put flow", "kimchi BTC/ETH v8.4", "S6 top-trader crowding",
           "M5 leverage build-up", "stablecoin impulse", "fee pressure"]                                   # Gen391 order


def _overlay(base: Path, live_rel: str) -> pd.DataFrame:
    frames = [pd.read_parquet(base)] if base.exists() else []
    if LIVE is not None and (LIVE / live_rel).exists():
        frames.append(pd.read_parquet(LIVE / live_rel))
    d = pd.concat(frames); d.index = pd.DatetimeIndex(d.index)
    if d.index.tz is not None:
        d.index = d.index.tz_localize(None)
    return d[~d.index.duplicated(keep="last")].sort_index()


def _cut_daily(s: pd.Series) -> pd.Series:                 # a day's value is known once that day is over
    return s[s.index.floor("D") + pd.Timedelta(days=1) <= CUT] if CUT is not None else s


def _cut_hourly(s: pd.Series) -> pd.Series:
    return s[s.index + pd.Timedelta(hours=1) <= CUT] if CUT is not None else s


def z(x, w):
    return (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()


def daily(s, how="last"):                                     # value of day d -> row d + 1 (as the Gen376-391 research)
    s = s.copy(); s.index = pd.DatetimeIndex(s.index).floor("D"); s = getattr(s.groupby(level=0), how)()
    return s.reindex(DAYS).ffill().shift(1)


# ------------------------------------------------------------------ basket members (daily target weights, BTC / ETH)
def _usdt_premium():
    ut = _cut_hourly(_overlay(ROOT / "research_data/coinbase/USDT-USD_1h.parquet", "coinbase/USDT-USD_1h.parquet")["close"])
    p24 = (ut - 1).rolling(24, min_periods=20).mean(); zz = (p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()
    zd = zz[zz.index.hour == 23]; zd.index = zd.index.floor("D"); zd = zd.reindex(DAYS)
    s = pd.Series(np.where(zd > 1, 0.25, np.where(zd < -1, -0.25, 0.0)), index=DAYS); return pd.DataFrame({"BTC": s, "ETH": s})


def _mint_shock():
    from qpl.lab.data import stablecoin_caps
    cap = stablecoin_caps(); cap = cap.where(cap > 0).loc["2019":]; g = cap.pct_change().shift(2).reindex(DAYS)
    sig = (g > 0.005).astype(float).rolling(3, min_periods=1).max(); return pd.DataFrame({"BTC": 0.5 * sig, "ETH": 0.5 * sig})


def _optflow(cur):
    fs = sorted(glob.glob(str(ROOT / f"research_data/more2/deribit_{cur}_optflow_*.parquet")))
    d = pd.concat([pd.read_parquet(f) for f in fs]); d["time"] = pd.to_datetime(d["time"]); d = d.set_index("time")
    if LIVE is not None and (LIVE / "ml" / f"deribit_{cur}_optflow_live.parquet").exists():
        lv = pd.read_parquet(LIVE / "ml" / f"deribit_{cur}_optflow_live.parquet"); lv.index = pd.DatetimeIndex(lv.index); d = pd.concat([d, lv])
    d = d[~d.index.duplicated(keep="last")].sort_index()
    d = d[d.index + pd.Timedelta(hours=1) <= CUT] if CUT is not None else d
    return (d.net_buy_C - d.net_buy_P).groupby(d.index.floor("D")).sum(min_count=1)


def _call_put_flow():
    W = pd.DataFrame(0.0, index=pd.date_range("2020-01-01", DAYS[-1]), columns=["BTC", "ETH"])
    for c in ("BTC", "ETH"):
        f = _optflow(c).reindex(W.index); z2 = (f - f.rolling(30, min_periods=20).mean()) / f.rolling(30, min_periods=20).std()
        W[c] = np.where(z2 > 1.5, 0.5, np.where(z2 < -1.5, -0.5, 0.0))
    return W


def _kimchi():
    import ridge_live as RL
    zk = pd.DataFrame({c: RL.zk_strict(c, B.k5(c).close.resample("1h").last()) for c in ("BTC", "ETH")})
    return pd.DataFrame(np.where(zk > 1, 0.5, np.where(zk < -1, -0.5, 0.0)), index=zk.index, columns=zk.columns)


def _top_trader():
    return pd.DataFrame({c: -0.125 * z(daily(B.metrics(c)["count_toptrader_long_short_ratio"], "mean"), 90).clip(-2, 2) / 2 for c in ("BTC", "ETH")})


def _leverage():
    return pd.DataFrame({c: -0.125 * z(np.log(daily(B.metrics(c)["sum_open_interest_value"].where(lambda s: s > 0))).diff(7), 90).clip(-2, 2) / 2 for c in ("BTC", "ETH")})


def _stable_impulse():
    st = daily(_cut_daily(_overlay(ND / "defillama_stablecoins.parquet", "ml/defillama_stablecoins.parquet")["stablecoin_usd"]))
    n2 = z(np.log(st).diff(30), 365); return pd.DataFrame({"BTC": 0.125 * n2.clip(-2, 2) / 2, "ETH": 0.125 * n2.clip(-2, 2) / 2})


def _fees():
    n3 = z(daily(_cut_daily(_overlay(ND / "bc_transaction-fees-usd.parquet", "ml/bc_transaction-fees-usd.parquet")["transaction-fees-usd"])), 90)
    return pd.DataFrame({"BTC": -0.25 * n3.clip(-2, 2) / 2})


BUILD = {"Gen249 A USDT premium": _usdt_premium, "mint shock": _mint_shock, "Gen120 D2 call-minus-put flow": _call_put_flow, "kimchi BTC/ETH v8.4": _kimchi,
         "S6 top-trader crowding": _top_trader, "M5 leverage build-up": _leverage, "stablecoin impulse": _stable_impulse, "fee pressure": _fees}


def basket(index):
    """(hourly P&L of the basket on `index`, dict of daily per-coin weight frames already multiplied by the basket scale)."""
    W, P = {}, {}
    for k in MEMBERS:
        w = BUILD[k]().reindex(DAYS).fillna(0.0)
        W[k] = w
        P[k] = CS._from_daily_weights(w, list(w.columns), 5).reindex(index).fillna(0.0)
    sd = pd.Series({k: P[k].groupby(P[k].index.floor("D")).sum().loc["2022":"2024"].std() for k in MEMBERS})
    raw = sum(P[k] / sd[k] for k in MEMBERS); rd = raw.groupby(raw.index.floor("D")).sum()
    k_ = 0.15 / (rd.loc["2022":"2024"].std() * np.sqrt(365))
    scaled = {k: W[k] * (k_ / sd[k]) for k in MEMBERS}
    return raw * k_, scaled


# ------------------------------------------------------------------ relative crowding (6 coins)
def _rel_daily(col, win=90):
    Zs = pd.DataFrame({c: z(daily(B.metrics(c)[col], "mean"), win) for c in C6}); Zd = Zs.sub(Zs.mean(axis=1), axis=0)
    return (-0.15 * Zd.clip(-2, 2) / 2).where(Zs.notna().all(axis=1), 0.0)


def _rel_8h(col):
    Zs = {}
    for c in C6:
        m = B.metrics(c)[col]; x = m.resample("8h").mean()
        Zs[c] = (x - x.rolling(270, min_periods=190).mean()) / x.rolling(270, min_periods=190).std()
    Zs = pd.DataFrame(Zs); Zd = Zs.sub(Zs.mean(axis=1), axis=0)
    return (-0.15 * Zd.clip(-2, 2) / 2).where(Zs.notna().all(axis=1), 0.0)


def rc_weights():
    """daily frames (row d held during d+1 after the book's own one-day shift in _rc_pnl) and the 8-hour frame (bar-close stamped)."""
    cols = ("count_toptrader_long_short_ratio", "count_long_short_ratio")
    d = {c: _rel_daily(c) for c in cols}
    return {"daily": d, "smooth": {c: v.rolling(3, min_periods=1).mean() for c, v in d.items()}, "h8": {c: _rel_8h(c) for c in cols}}


def _hourly_ret(c, index):
    r = B.k5(c).close.resample("1h").last().pct_change().reindex(index).fillna(0.0)
    f = B.funding(c).copy(); f.index = f.index - pd.Timedelta(hours=1); f = f.groupby(level=0).sum().reindex(index).fillna(0.0)
    return r, f


def rc_positions(index, RW=None):
    """hourly per-coin positions of the relative crowding sleeve (mean of the three versions, each the mean of two metrics)."""
    RW = RW or rc_weights(); pos = pd.DataFrame(0.0, index=index, columns=list(C6))
    for kind in ("daily", "smooth"):
        for w in RW[kind].values():
            pos += w.reindex(DAYS).fillna(0.0).shift(1).reindex(index.floor("D")).set_axis(index).fillna(0.0) / 6
    for w in RW["h8"].values():
        p = w.copy(); p.index = p.index + pd.Timedelta(hours=8)
        pos += p.reindex(index, method="ffill").fillna(0.0) / 6
    return pos


def rc_pnl(index):
    """hourly P&L, accounted per version as in Gen401 / Gen404 (turnover per version, 5 bp, funding)."""
    RW = rc_weights(); out = 0.0
    R = {c: _hourly_ret(c, index) for c in C6}
    def one(pos):
        x = 0.0
        for c in C6:
            p = pos[c]; r, f = R[c]; x = x + p * r - p * f - p.diff().abs().fillna(0.0) * 5 / 1e4
        return x
    for kind in ("daily", "smooth"):
        for w in RW[kind].values():
            out = out + one(w.reindex(DAYS).fillna(0.0).shift(1).reindex(index.floor("D")).set_axis(index).fillna(0.0)) / 6
    for w in RW["h8"].values():
        p = w.copy(); p.index = p.index + pd.Timedelta(hours=8); out = out + one(p.reindex(index, method="ffill").fillna(0.0)) / 6
    return out, RW


# ------------------------------------------------------------------ ensembles (Gen383)
def trend_ensemble():
    outs = [CS.trend4h(n_in=n, n_out=n // 2, positions=True) for n in (15, 20, 30)]
    pnl = sum(o[0] for o in outs) / 3; pos = sum(o[1] for o in outs) / 3
    return pnl, pos


def altk_ensemble(end):
    import alt_kimchi as AK
    ws = [AK.weights(end, th=t) for t in (0.75, 1.0, 1.25)]
    pnl = sum(CS._from_daily_weights(w, list(w.columns), 5) for w in ws) / 3; w = sum(ws) / 3
    return pnl, w

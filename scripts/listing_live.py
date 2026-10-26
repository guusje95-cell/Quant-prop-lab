"""v9.6 listing-short sleeve for paper trading (Gen426, accepted 2026-10-26). Point-in-time: honours QPL_CUTOFF and the
QPL_LIVE_PACK overlay (<live>/listings/<SYM>_1h.parquet, <SYM>_funding.parquet from qpl.live.binance_public.update_listings).

Rule: every USDT-M perp first listed on or after 2021-06-01 (TradFi perps excluded) with >= $10M quote volume in its first 24 hours
is shorted 0.05 from the first UTC midnight at least 24 h after its first bar, for 30 days; the short is covered for good once a
close is 30% above the entry close. Total gross capped at 0.5. 10 bp per side, real funding.

Timing (the framework of the other sleeves): the position held during hour [t, t+1h) uses only closes known at t; the stop and
the entry are decided one hour after the close that triggers them (as in the Gen426 research), and a coin whose latest bar is
missing (delisted or no data yet) is flat. History: research_data/binance_pit (symbols A..S until the rest is downloaded)."""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PIT = ROOT / "research_data/binance_pit"
LIVE = Path(os.environ["QPL_LIVE_PACK"]) / "listings" if os.environ.get("QPL_LIVE_PACK") else None
CUT = pd.Timestamp(os.environ["QPL_CUTOFF"]) if os.environ.get("QPL_CUTOFF") else None
SIZE, CAP, HOLD, STOP, MINVOL, COST_BP = 0.05, 0.5, 30, 0.30, 1e7, 10.0
FIRST = pd.Timestamp("2021-06-01")


def _read(sym: str):
    """(hourly close/quote_volume frame, funding series stamped at settlement) from the research archive + live overlay, cut."""
    ks, fs = [], []
    for base in (PIT, LIVE):
        if base is None:
            continue
        if (base / f"{sym}_1h.parquet").exists():
            k = pd.read_parquet(base / f"{sym}_1h.parquet")[["close", "quote_volume"]]; k.index = pd.DatetimeIndex(k.index); ks.append(k)
        if (base / f"{sym}_funding.parquet").exists():
            f = pd.read_parquet(base / f"{sym}_funding.parquet"); fs.append(pd.Series(f["last_funding_rate"].to_numpy(), index=pd.to_datetime(f["time"]).dt.floor("h")))
    if not ks:
        return None, None
    k = pd.concat(ks); k = k[~k.index.duplicated(keep="last")].sort_index().astype(float)
    f = pd.concat(fs).groupby(level=0).last().sort_index() if fs else pd.Series(dtype=float)
    if CUT is not None:
        k = k[k.index + pd.Timedelta(hours=1) <= CUT]; f = f[f.index <= CUT]
    return k, f


def symbols() -> list[str]:
    tf = set(json.loads((ROOT / "config/tradfi_perps.json").read_text())["symbols"])
    names = set()
    for base in (PIT, LIVE):
        if base is not None and base.exists():
            names |= {Path(p).name[:-len("_1h.parquet")] for p in glob.glob(str(base / "*_1h.parquet")) if not p.endswith("premium_1h.parquet")}
    return sorted(s for s in names if s.endswith("USDT") and s[:-4] not in tf)          # tradfi_perps.json lists base names (AAPL, XAU)


def events():
    """[(symbol, first bar, closes, funding)] for qualifying listings (first-day volume known by the entry time)."""
    out = []
    for s in symbols():
        k, f = _read(s)
        if k is None or len(k) == 0:
            continue
        t0 = k.index.min()
        if t0 < FIRST or k.index.max() < t0 + pd.Timedelta(hours=23):
            continue
        if k.loc[:t0 + pd.Timedelta(hours=23), "quote_volume"].sum() < MINVOL:
            continue
        out.append((s, t0, k["close"], f))
    return out


def positions(index: pd.DatetimeIndex, EV=None) -> pd.DataFrame:
    """Hourly positions (fractions of unit equity, negative = short) on `index`, columns = coin names without USDT."""
    EV = events() if EV is None else EV
    P = {}
    for s, t0, c, _ in EV:
        start = (t0 + pd.Timedelta(hours=24)).ceil("D"); end = start + pd.Timedelta(days=HOLD)
        if start > index[-1] + pd.Timedelta(hours=1) or end <= index[0]:
            continue
        cc = c.loc[start:end]
        if len(cc) == 0:
            continue
        hit = cc[cc >= cc.iloc[0] * (1 + STOP)].index
        last = hit[0] if len(hit) else end - pd.Timedelta(hours=1)                    # last decision bar
        dec = pd.Series(SIZE * -1.0, index=c.loc[start:last].index)                   # bars start .. stop bar (closes known at t + 1h) ...
        p = dec.copy(); p.index = p.index + pd.Timedelta(hours=1)                     # ... held during [t+1h, t+2h): Gen426 timing
        p = p.reindex(index).fillna(0.0)
        alive = c.reindex(index - pd.Timedelta(hours=1)).notna().to_numpy()           # the previous bar exists (not delisted)
        P[s[:-4]] = p.where(alive, 0.0)
    if not P:
        return pd.DataFrame(index=index)
    pos = pd.DataFrame(P)
    g = pos.abs().sum(axis=1)
    return pos.mul((CAP / g).clip(upper=1.0).fillna(1.0), axis=0)


def pnl(index: pd.DatetimeIndex):
    """(hourly P&L on `index`, positions frame, events)."""
    EV = events(); pos = positions(index, EV); out = pd.Series(0.0, index=index)
    for s, t0, c, f in EV:
        n = s[:-4]
        if n not in pos:
            continue
        p = pos[n]
        r = (c / c.shift(1) - 1).reindex(index).fillna(0.0)                            # bar t: return during [t, t+1h)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(index).fillna(0.0)   # paid on the hour ending at the stamp
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * COST_BP / 1e4
    return out, pos, EV

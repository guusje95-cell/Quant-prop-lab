"""Point-in-time universe helpers (Gen410 / 445 / 446 / 447): membership of the top-N by trailing 30-day quote volume and hourly data
for any USDT-M perp from the 20-coin pack, the 40 extra coins or research_data/binance_pit (delisted included, TradFi excluded).

  members(n)     daily bool frame: coin in the top-n (set on the first day of each month from days before, >= 60 days listed)
  frame(c)       hourly c / lo / hi / v (quote volume) / oi (open-interest value) or None
  ret_funding(c) (hourly return of bar t = close(t) / close(t-1) - 1, funding charged on the hour ending at the stamp)
  ratios(c)      5-minute metrics with the long/short ratio columns (pack, or the cached archive download) or None"""
from __future__ import annotations

import glob
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

import gen57_cascade_hourly as CH
from qpl.lab import binance_pack as B

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "research_data/binance_extra"; PIT = ROOT / "research_data/binance_pit"; ARCH = ROOT / "data/lab/binance_vision"
END = "2026-09-30"
TF = set(json.loads((ROOT / "config/tradfi_perps.json").read_text())["symbols"])
PACK = list(B.coins())
EXTRA = sorted(p.name[:-len("USDT_1h.parquet")] for p in EX.glob("*USDT_1h.parquet"))


@lru_cache(maxsize=None)
def _qv_daily() -> pd.DataFrame:
    qv = {}
    for f in glob.glob(str(PIT / "*USDT_1h.parquet")):
        c = Path(f).name[:-len("USDT_1h.parquet")]
        if c in TF or not c.isascii():
            continue
        qv[c] = pd.read_parquet(f, columns=["quote_volume"])["quote_volume"].astype(float).resample("1D").sum()
    for c in EXTRA:
        qv[c] = pd.read_parquet(EX / f"{c}USDT_1h.parquet")["quote_volume"].astype(float).resample("1D").sum()
    for c in PACK:
        qv[c] = B.k5(c).quote_volume.resample("1D").sum()
    return pd.DataFrame(qv).loc[:END]


@lru_cache(maxsize=None)
def members(n: int) -> pd.DataFrame:
    Q = _qv_daily(); age = Q.notna().cumsum(); v30 = Q.rolling(30, min_periods=20).sum().shift(1)
    first = ~Q.index.to_period("M").duplicated()
    return (v30.where(age.shift(1) >= 60).rank(axis=1, ascending=False) <= n)[first].reindex(Q.index).ffill().fillna(False).astype(bool)


@lru_cache(maxsize=None)
def frame(c: str):
    if c in PACK:
        d = CH.hourly(c).copy()
    elif c in EXTRA:
        k = pd.read_parquet(EX / f"{c}USDT_1h.parquet"); o = pd.read_parquet(EX / f"{c}USDT_oi_1h.parquet")
        d = pd.DataFrame({"c": k["close"], "lo": k["low"], "hi": k["high"], "v": k["quote_volume"]}).astype(float)
        o.index = pd.DatetimeIndex(o.index).as_unit("ns"); d.index = pd.DatetimeIndex(d.index).as_unit("ns")
        d["oi"] = o.iloc[:, 0].astype(float).reindex(d.index)
    else:
        f, g = PIT / f"{c}USDT_hl_1h.parquet", PIT / f"{c}USDT_oi_1h.parquet"
        if not f.exists() or not g.exists():
            return None
        k = pd.read_parquet(f); d = pd.DataFrame({"c": k["close"], "lo": k["low"], "hi": k["high"], "v": k["quote_volume"]}).astype(float)
        o = pd.read_parquet(g); o.index = pd.DatetimeIndex(o.index).as_unit("ns"); d.index = pd.DatetimeIndex(d.index).as_unit("ns")
        d["oi"] = o["oi_value"].astype(float).reindex(d.index)
    d.index = pd.DatetimeIndex(d.index).as_unit("ns")
    return d.loc[:END + " 23:00"]


@lru_cache(maxsize=None)
def ret_funding(c: str):
    if c in PACK:
        r = B.k5(c).close.resample("1h").last().pct_change(); f = B.funding(c).copy()
    else:
        d = frame(c)
        if d is None:
            return None
        r = d["c"].pct_change()
        src = EX / f"{c}USDT_funding.parquet" if c in EXTRA else PIT / f"{c}USDT_funding.parquet"
        x = pd.read_parquet(src); f = pd.Series(x["last_funding_rate"].astype(float).to_numpy(), index=pd.to_datetime(x["time"]))
    f.index = pd.DatetimeIndex(f.index).floor("h") - pd.Timedelta(hours=1)
    return r.fillna(0.0), f.groupby(level=0).sum()


@lru_cache(maxsize=None)
def ratios(c: str):
    if c in PACK:
        return B.metrics(c)
    p = ARCH / f"{c}USDT_metrics.parquet"
    if not p.exists():
        return None
    x = pd.read_parquet(p); x.index = pd.to_datetime(x["time"]); return x.drop(columns=[k for k in ("time",) if k in x]).sort_index()


def pnl_from_hourly_positions(P: pd.DataFrame, idx: pd.DatetimeIndex, cost_bp: float = 5.0) -> pd.Series:
    out = pd.Series(0.0, index=idx)
    for c in P.columns:
        rf = ret_funding(c)
        if rf is None:
            continue
        r, f = rf; p = P[c].reindex(idx).fillna(0.0)
        out = out + p * r.reindex(idx).fillna(0.0) - p * f.reindex(idx).fillna(0.0) - p.diff().abs().fillna(p.abs()) * cost_bp / 1e4
    return out

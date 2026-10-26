"""Loader for the user's Binance USD-M research pack (research_data/binance/): 5-minute klines (with trade counts and taker-buy
volume), 5-minute metrics (open interest, long/short ratios, taker ratio; 2021-12+), 8h funding and hourly premium index."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "research_data" / "binance"
# Paper trading: QPL_LIVE_PACK = folder with newer files in the same format (appended after the pack, newer rows win);
# QPL_CUTOFF = UTC time "now": rows that were not yet known at that time are dropped (5m bars that close after it, etc.).
LIVE = Path(os.environ["QPL_LIVE_PACK"]) if os.environ.get("QPL_LIVE_PACK") else None
CUTOFF = pd.Timestamp(os.environ["QPL_CUTOFF"]) if os.environ.get("QPL_CUTOFF") else None


def _read(name: str) -> pd.DataFrame:
    parts = [pd.read_parquet(PACK / name)]
    if LIVE is not None and (LIVE / name).exists():
        parts.append(pd.read_parquet(LIVE / name))
    return pd.concat(parts) if len(parts) > 1 else parts[0]


def _known(idx: pd.DatetimeIndex, bar: str | None) -> "pd.Series | slice":
    """Boolean mask of rows known at CUTOFF (bar = bar length for klines, None for point-in-time records)."""
    if CUTOFF is None:
        return slice(None)
    end = idx + pd.Timedelta(bar) if bar else idx
    return end <= CUTOFF


MAJ10 = ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "AVAX", "DOT", "LINK"]


def coins() -> list[str]:
    return sorted(p.stem.replace("USDT_5m", "") for p in PACK.glob("*USDT_5m.parquet"))


@lru_cache(maxsize=64)
def k5(coin: str) -> pd.DataFrame:
    d = _read(f"{coin}USDT_5m.parquet").astype("float64")
    d.index = pd.DatetimeIndex(d.index)
    d = d[~d.index.duplicated(keep="last")].sort_index()
    return d[_known(d.index, "5min")]


def panel(field: str = "close", rule: str = "5min", coins_=None) -> pd.DataFrame:
    """Wide panel of one field; rule e.g. '1h' or '1D' (label = bar open time; last for prices, sum for volumes)."""
    out = {}
    for c in coins_ or coins():
        d = k5(c)[field]
        if rule != "5min":
            how = "last" if field in ("close",) else ("first" if field == "open" else ("max" if field == "high" else ("min" if field == "low" else "sum")))
            d = getattr(d.resample(rule), how)()
        out[c] = d
    return pd.DataFrame(out).sort_index()


@lru_cache(maxsize=64)
def funding(coin: str) -> pd.Series:
    d = _read(f"{coin}USDT_funding.parquet")
    t = pd.to_datetime(d["time"]).dt.round("h")
    s = pd.Series(d["last_funding_rate"].astype(float).to_numpy(), index=t).groupby(level=0).last().sort_index()
    return s[_known(s.index, None)]


@lru_cache(maxsize=64)
def metrics(coin: str) -> pd.DataFrame:
    d = _read(f"{coin}USDT_metrics.parquet")
    d["time"] = pd.to_datetime(d["time"])
    d = d.drop_duplicates("time", keep="last").set_index("time").sort_index()
    d = d.apply(pd.to_numeric, errors="coerce")
    if LIVE is not None and (LIVE / f"{coin}USDT_ratios.parquet").exists():          # v9.5: live ratios fill the NaN ratio columns
        r = pd.read_parquet(LIVE / f"{coin}USDT_ratios.parquet"); r.index = pd.DatetimeIndex(r.index)
        r = r[~r.index.duplicated(keep="last")].reindex(d.index)
        for col in r.columns:
            if col in d:
                d[col] = d[col].fillna(r[col])
    return d[_known(d.index, None)]


@lru_cache(maxsize=64)
def premium(coin: str) -> pd.DataFrame:
    d = _read(f"{coin}USDT_premium_1h.parquet")
    d["time"] = pd.to_datetime(d["time"])
    d = d.drop_duplicates("time", keep="last").set_index("time").sort_index()[["open", "high", "low", "close"]]
    return d[_known(d.index, "1h")]


def funding_panel(coins_=None) -> pd.DataFrame:
    return pd.DataFrame({c: funding(c) for c in coins_ or coins()}).sort_index()

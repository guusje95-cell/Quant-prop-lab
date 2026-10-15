"""Loader for the user's Binance USD-M research pack (research_data/binance/): 5-minute klines (with trade counts and taker-buy
volume), 5-minute metrics (open interest, long/short ratios, taker ratio; 2021-12+), 8h funding and hourly premium index."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "research_data" / "binance"
MAJ10 = ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "AVAX", "DOT", "LINK"]


def coins() -> list[str]:
    return sorted(p.stem.replace("USDT_5m", "") for p in PACK.glob("*USDT_5m.parquet"))


@lru_cache(maxsize=64)
def k5(coin: str) -> pd.DataFrame:
    d = pd.read_parquet(PACK / f"{coin}USDT_5m.parquet").astype("float64")
    d.index = pd.DatetimeIndex(d.index)
    return d[~d.index.duplicated()].sort_index()


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
    d = pd.read_parquet(PACK / f"{coin}USDT_funding.parquet")
    t = pd.to_datetime(d["time"]).dt.round("h")
    return pd.Series(d["last_funding_rate"].astype(float).to_numpy(), index=t).groupby(level=0).last().sort_index()


@lru_cache(maxsize=64)
def metrics(coin: str) -> pd.DataFrame:
    d = pd.read_parquet(PACK / f"{coin}USDT_metrics.parquet")
    d["time"] = pd.to_datetime(d["time"])
    d = d.drop_duplicates("time").set_index("time").sort_index()
    return d.apply(pd.to_numeric, errors="coerce")


@lru_cache(maxsize=64)
def premium(coin: str) -> pd.DataFrame:
    d = pd.read_parquet(PACK / f"{coin}USDT_premium_1h.parquet")
    d["time"] = pd.to_datetime(d["time"])
    return d.drop_duplicates("time").set_index("time").sort_index()[["open", "high", "low", "close"]]


def funding_panel(coins_=None) -> pd.DataFrame:
    return pd.DataFrame({c: funding(c) for c in coins_ or coins()}).sort_index()

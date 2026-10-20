"""Loader for the extra Binance USD-M coins (research_data/binance_extra/, Gen80): hourly klines, funding, hourly premium index.
Same live conventions as binance_pack: QPL_LIVE_PACK/extra/ holds newer rows in the same format (newer rows win); QPL_CUTOFF drops
rows not yet known at that time (an hourly bar counts once its hour is over)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "research_data" / "binance_extra"
LIVE = Path(os.environ["QPL_LIVE_PACK"]) / "extra" if os.environ.get("QPL_LIVE_PACK") else None
CUTOFF = pd.Timestamp(os.environ["QPL_CUTOFF"]) if os.environ.get("QPL_CUTOFF") else None
# BrightFunded-listed coins among the pack and extra coins (MT5 export 2026-10-19), used by the bf-b book (Gen121)
BF_NEW = ["AAVE", "ATOM", "BNB", "ETC", "FIL", "NEAR", "TRX", "UNI", "XLM", "ALGO", "APT", "ARB", "COMP", "CRV", "DASH", "DYDX", "EGLD",
          "GRT", "HBAR", "ICP", "INJ", "LDO", "MANA", "NEO", "OP", "RUNE", "SAND", "SNX", "STX", "SUI", "XTZ"]


def coins() -> list[str]:
    return sorted(p.stem.replace("USDT_1h", "") for p in PACK.glob("*USDT_1h.parquet"))


def _frames(name: str):
    parts = [pd.read_parquet(PACK / name)]
    if LIVE is not None and (LIVE / name).exists():
        parts.append(pd.read_parquet(LIVE / name))
    return parts


@lru_cache(maxsize=128)
def close_1h(coin: str) -> pd.Series:
    parts = []
    for d in _frames(f"{coin}USDT_1h.parquet"):
        if "time" in d:
            d = d.set_index("time")
        parts.append(d["close"].astype(float))
    s = pd.concat(parts); s.index = pd.DatetimeIndex(s.index); s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s.index + pd.Timedelta(hours=1) <= CUTOFF] if CUTOFF is not None else s


@lru_cache(maxsize=128)
def premium(coin: str) -> pd.Series:
    d = pd.concat(_frames(f"{coin}USDT_premium_1h.parquet")); d["time"] = pd.to_datetime(d["time"])
    s = d.drop_duplicates("time", keep="last").set_index("time").sort_index()["close"].astype(float)
    return s[s.index + pd.Timedelta(hours=1) <= CUTOFF] if CUTOFF is not None else s


@lru_cache(maxsize=128)
def funding(coin: str) -> pd.Series:
    d = pd.concat(_frames(f"{coin}USDT_funding.parquet")); t = pd.to_datetime(d["time"]).dt.round("h")
    s = pd.Series(d["last_funding_rate"].astype(float).to_numpy(), index=t).groupby(level=0).last().sort_index()
    return s[s.index <= CUTOFF] if CUTOFF is not None else s

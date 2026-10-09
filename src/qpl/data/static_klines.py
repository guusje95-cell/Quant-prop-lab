"""Binance SPOT klines for 10 majors from github.com/finom/static-klines (daily-updated public mirror of Binance public
market data; the author notes it is intended for backtests/analysis). 1d from 2017, 1h from 2022. Times are UTC.
Ingest: python -m qpl.data.static_klines <path to .klines-cache>"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROC = Path(__file__).resolve().parents[3] / "data/processed/crypto"
SYMBOLS = ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "AVAX", "DOT", "LINK"]
COLS = ["open", "high", "low", "close", "volume"]


def ingest(cache: Path, rule: str) -> pd.DataFrame:
    frames = []
    for s in SYMBOLS:
        rows = []
        for f in sorted((cache / f"{s}USDT" / rule).glob("*.json")):
            rows += json.loads(f.read_text() or "[]")
        if not rows:
            continue
        df = pd.DataFrame([r[:6] for r in rows], columns=["t"] + COLS).astype(float)
        df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("t").astype("int64"), unit="ms"))
        df = df[~df.index.duplicated()].sort_index()
        df.columns = pd.MultiIndex.from_product([[s], COLS])
        frames.append(df)
    out = pd.concat(frames, axis=1)
    PROC.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROC / f"binance_spot_majors_{rule}.parquet")
    return out


def load(rule: str = "1d") -> dict[str, pd.DataFrame]:
    """Returns {'open': DataFrame[date x symbol], 'high': ..., 'low': ..., 'close': ..., 'volume': ...}."""
    df = pd.read_parquet(PROC / f"binance_spot_majors_{rule}.parquet")
    return {k: df.xs(k, axis=1, level=1) for k in COLS}


if __name__ == "__main__":
    c = Path(sys.argv[1])
    for r in ("1d", "1h"):
        d = ingest(c, r)
        print(r, d.shape, d.index.min(), d.index.max())

"""Deribit public funding-rate history for BTC-PERPETUAL / ETH-PERPETUAL (hourly interest_1h, index price), 2019+.
Saved to data/raw/deribit/<INST>_funding.parquet (gitignored)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

RAW = Path(__file__).resolve().parents[3] / "data/raw/deribit"
URL = "https://www.deribit.com/api/v2/public/get_funding_rate_history?instrument_name={i}&start_timestamp={a}&end_timestamp={b}"


def funding(inst: str, start: str = "2019-05-01") -> pd.DataFrame:
    a = int(pd.Timestamp(start).timestamp() * 1000); now = int(time.time() * 1000); rows = []
    step = 20 * 86400 * 1000
    while a < now:
        r = requests.get(URL.format(i=inst, a=a, b=min(a + step, now)), timeout=30).json()["result"]
        rows += r; a += step; time.sleep(0.2)
    df = pd.DataFrame(rows).drop_duplicates("timestamp")
    df.index = pd.to_datetime(df.pop("timestamp"), unit="ms"); df = df.sort_index()
    RAW.mkdir(parents=True, exist_ok=True); df.to_parquet(RAW / f"{inst}_funding.parquet")
    return df


def load(inst: str) -> pd.DataFrame:
    return pd.read_parquet(RAW / f"{inst}_funding.parquet")


if __name__ == "__main__":
    for i in sys.argv[1:] or ["BTC-PERPETUAL", "ETH-PERPETUAL"]:
        d = funding(i); print(i, len(d), d.index.min(), d.index.max(), flush=True)

"""Dukascopy public datafeed (no account): yearly BID daily candles per instrument, 2003 -> today.
File: https://datafeed.dukascopy.com/datafeed/{SYM}/{YYYY}/BID_candles_day_1.bi5 (LZMA; 24-byte big-endian records:
uint32 seconds-from-year-start, int32 open, close, low, high (price * 10^digits), float32 volume).
Politeness: sequential, >= 1.5 s between requests, exponential backoff on HTTP 429. Saved to data/raw/dukascopy_direct/."""
from __future__ import annotations

import lzma
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

RAW = Path(__file__).resolve().parents[3] / "data/raw/dukascopy_direct"
URL = "https://datafeed.dukascopy.com/datafeed/{s}/{y}/BID_candles_day_1.bi5"
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "EURCHF",
           "XAUUSD", "XAGUSD", "LIGHTCMDUSD", "BRENTCMDUSD", "GASCMDUSD", "COPPERCMDUSD",
           "USA500IDXUSD", "USATECHIDXUSD", "USA30IDXUSD", "USSC2000IDXUSD", "DEUIDXEUR", "GBRIDXGBP", "JPNIDXJPY", "FRAIDXEUR", "EUSIDXEUR",
           "AUSIDXAUD", "HKGIDXHKD", "BUNDTREUR", "USTBONDTRUSD", "UKGILTTRGBP", "SOYBEANCMDUSX", "CORNCMDUSX", "WHEATCMDUSX", "SUGARCMDUSD",
           "COFFEECMDUSX", "COCOACMDUSD", "COTTONCMDUSX"]


def _fetch(url, tries=8):
    for k in range(tries):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 429:
                time.sleep(5 * 2 ** k); continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            time.sleep(5 * 2 ** k)
    return None


def year(sym, y):
    b = _fetch(URL.format(s=sym, y=y)); time.sleep(1.5)
    if not b:
        return None
    raw = lzma.decompress(b)
    dt = np.dtype([("t", ">u4"), ("o", ">i4"), ("c", ">i4"), ("l", ">i4"), ("h", ">i4"), ("v", ">f4")])
    a = np.frombuffer(raw[: len(raw) // 24 * 24], dtype=dt)
    rec = np.column_stack([a[k].astype(float) for k in ("t", "o", "c", "l", "h", "v")])
    if not len(rec):
        return None
    t = pd.Timestamp(f"{y}-01-01") + pd.to_timedelta(rec[:, 0], unit="s")
    return pd.DataFrame({"open": rec[:, 1], "close": rec[:, 2], "low": rec[:, 3], "high": rec[:, 4], "volume": rec[:, 5]}, index=t)


def download(sym, start=2003, end=2026):
    parts = [d for y in range(start, end + 1) if (d := year(sym, y)) is not None]
    if not parts:
        return None
    df = pd.concat(parts).sort_index(); df = df[~df.index.duplicated()]
    df = df[df.volume > 0]
    RAW.mkdir(parents=True, exist_ok=True); df.to_parquet(RAW / f"{sym}_D1_raw.parquet")
    return df


if __name__ == "__main__":
    for s in sys.argv[1:] or SYMBOLS:
        if (RAW / f"{s}_D1_raw.parquet").exists():
            continue
        d = download(s)
        print(s, "NONE" if d is None else (len(d), str(d.index.min().date()), str(d.index.max().date())), flush=True)

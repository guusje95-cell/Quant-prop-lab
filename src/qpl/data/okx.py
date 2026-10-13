"""OKX public market data (no API key): USDT-margined perpetual swap 1H candles (history-candles) and recent funding.
Rate limit: history-candles 20 req / 2 s -> we sleep 0.15 s per request. Data saved to data/raw/okx/<INST>_1H.parquet
(gitignored). Survivorship note: the universe is chosen from instruments live in 2026-10 (delisted coins missing)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

RAW = Path(__file__).resolve().parents[3] / "data/raw/okx"
BASE = "https://www.okx.com/api/v5"


def _get(url: str, tries: int = 5):
    for k in range(tries):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 429:
                time.sleep(2 * (k + 1)); continue
            r.raise_for_status()
            d = r.json()
            if d.get("code") == "0":
                return d["data"]
            if d.get("code") in ("50011",):          # rate limit
                time.sleep(2 * (k + 1)); continue
            raise RuntimeError(d)
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 * (k + 1))


def candles_1h(inst: str, start_ms: int = 1546300800000) -> pd.DataFrame:
    """All 1H candles from start_ms (default 2019-01-01) to now, oldest first; only confirmed candles."""
    p = RAW / f"{inst}_1H.parquet"
    rows, after = [], None
    while True:
        url = f"{BASE}/market/history-candles?instId={inst}&bar=1H&limit=100" + (f"&after={after}" if after else "")
        d = _get(url)
        time.sleep(0.15)
        if not d:
            break
        rows += d
        after = d[-1][0]
        if int(after) <= start_ms:
            break
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "vol", "volCcy", "volQuote", "confirm"])
    df = df[df.confirm == "1"].drop(columns="confirm")
    df.index = pd.to_datetime(df.pop("ts").astype("int64"), unit="ms")
    df = df.astype(float).sort_index()
    df = df[~df.index.duplicated()]
    df = df[df.index >= pd.Timestamp(start_ms, unit="ms")]
    RAW.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p)
    return df


def load_1h(inst: str) -> pd.DataFrame:
    return pd.read_parquet(RAW / f"{inst}_1H.parquet")


def _one(inst):
    if (RAW / f"{inst}_1H.parquet").exists():
        return
    t = time.time()
    try:
        d = candles_1h(inst)
        print(inst, len(d), d.index.min(), d.index.max(), f"{time.time() - t:.0f}s", flush=True)
    except Exception as e:
        print(inst, "FAILED", e, flush=True)


if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(6) as ex:                 # 6 workers x ~1.4 req/s each stays under OKX's 10 req/s
        list(ex.map(_one, sys.argv[1:]))

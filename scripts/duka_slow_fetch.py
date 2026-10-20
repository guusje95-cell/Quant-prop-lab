"""Resumable, slow Dukascopy daily-candle fetch (respects HTTP 429: waits and retries; 20 s between requests).
Usage: python scripts/duka_slow_fetch.py SYM [SYM ...]. Saves per-year parts in data/raw/dukascopy_direct/parts and assembles SYM_D1_raw.parquet."""
import sys
import time
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
import qpl.data.dukascopy_direct as DD
import lzma, numpy as np, requests
PARTS = DD.RAW / "parts"; PARTS.mkdir(parents=True, exist_ok=True)


def fetch(sym, y):
    f = PARTS / f"{sym}_{y}.parquet"
    if f.exists():
        return
    for k in range(12):
        r = requests.get(DD.URL.format(s=sym, y=y), timeout=60)
        if r.status_code == 429:
            time.sleep(60 * (k + 1)); continue
        if r.status_code == 404:
            pd.DataFrame().to_parquet(f); return
        r.raise_for_status(); break
    else:
        raise RuntimeError(f"{sym} {y}: still rate-limited")
    raw = lzma.decompress(r.content)
    dt = np.dtype([("t", ">u4"), ("o", ">i4"), ("c", ">i4"), ("l", ">i4"), ("h", ">i4"), ("v", ">f4")])
    a = np.frombuffer(raw[: len(raw) // 24 * 24], dtype=dt)
    t = pd.Timestamp(f"{y}-01-01") + pd.to_timedelta(a["t"].astype(float), unit="s")
    pd.DataFrame({"open": a["o"].astype(float), "close": a["c"].astype(float), "low": a["l"].astype(float), "high": a["h"].astype(float), "volume": a["v"].astype(float)}, index=t).to_parquet(f)
    print(sym, y, len(a), flush=True); time.sleep(20)


for sym in sys.argv[1:]:
    for y in range(2003, 2027):
        fetch(sym, y)
    parts = [pd.read_parquet(p) for p in sorted(PARTS.glob(f"{sym}_*.parquet"))]
    df = pd.concat([p for p in parts if len(p)]).sort_index(); df = df[~df.index.duplicated()]; df = df[df.volume > 0]
    df.to_parquet(DD.RAW / f"{sym}_D1_raw.parquet")
    SHARE = ROOT / "research_data/dukascopy_daily"; SHARE.mkdir(parents=True, exist_ok=True); df.to_parquet(SHARE / f"{sym}_D1_raw.parquet")
    print(sym, "DONE", len(df), df.index.min().date(), df.index.max().date(), flush=True)

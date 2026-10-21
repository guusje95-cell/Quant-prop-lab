"""Bitfinex public stats (no account): hourly margin position sizes (longs / shorts) for BTC and ETH, 2020+.
    python -m qpl.live.bitfinex_stats  -> research_data/bitfinex/<PAIR>_<side>_1h.parquet"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "bitfinex"
URL = "https://api-pub.bitfinex.com/v2/stats1/pos.size:1h:{p}:{s}/hist?start={a}&limit=10000&sort=1"


def fetch(pair, side, start="2020-01-01"):
    OUT.mkdir(parents=True, exist_ok=True); f = OUT / f"{pair}_{side}_1h.parquet"
    a = int(pd.Timestamp(start).timestamp() * 1000); rows = []
    while True:
        for k in range(5):
            try:
                with urllib.request.urlopen(urllib.request.Request(URL.format(p=pair, s=side, a=a), headers={"User-Agent": "qpl research"}), timeout=30) as r:
                    js = json.loads(r.read()); break
            except Exception:
                time.sleep(5 * (k + 1))
        else:
            raise RuntimeError(f"{pair} {side}: giving up")
        if not js:
            break
        rows += js; last = js[-1][0]
        if len(js) < 10000:
            break
        a = last + 1; time.sleep(2)
    d = pd.DataFrame(rows, columns=["t", "size"]); d.index = pd.to_datetime(d.pop("t"), unit="ms"); d = d[~d.index.duplicated()].sort_index()
    d.to_parquet(f); print(f"{pair} {side}: {len(d)} rows {d.index.min()} .. {d.index.max()}", flush=True)


if __name__ == "__main__":
    for p in ("tBTCUSD", "tETHUSD"):
        for s in ("long", "short"):
            fetch(p, s)

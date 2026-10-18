"""Coinbase Exchange public hourly candles (no account, no key) for the Gen88 Coinbase-premium test.

    python -m qpl.live.coinbase_public           # BTC-USD, ETH-USD hourly from 2020-01-01 -> research_data/coinbase/<PRODUCT>_1h.parquet

Public endpoint, 300 candles per request, paced well under the published public rate limit; resumable."""
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "coinbase"
URL = "https://api.exchange.coinbase.com/products/{p}/candles?granularity=3600&start={s}&end={e}"
PRODUCTS = ("BTC-USD", "ETH-USD")


def fetch(product, start, end):
    req = urllib.request.Request(URL.format(p=product, s=start.strftime("%Y-%m-%dT%H:%M:%SZ"), e=end.strftime("%Y-%m-%dT%H:%M:%SZ")),
                                 headers={"User-Agent": "quant-prop-lab research"})
    for k in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as ex:                       # 429 / network: back off and retry
            time.sleep(2 ** (k + 1)); err = ex
    raise RuntimeError(f"{product} {start}: {err}")


def update(product, since="2020-01-01"):
    OUT.mkdir(parents=True, exist_ok=True); f = OUT / f"{product}_1h.parquet"
    old = pd.read_parquet(f) if f.exists() else None
    t = (old.index[-1].to_pydatetime().replace(tzinfo=timezone.utc) + timedelta(hours=1)) if old is not None and len(old) else \
        datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0); rows = []
    while t < now:
        e = min(t + timedelta(hours=299), now)
        rows += fetch(product, t, e); t = e + timedelta(hours=1); time.sleep(0.4)
        if len(rows) % 6000 < 300:
            print(f"  {product} up to {e:%Y-%m-%d}", flush=True)
    if rows:
        d = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "volume"])
        d.index = pd.to_datetime(d.pop("t"), unit="s"); d = d.sort_index()
        d = pd.concat([old, d]) if old is not None else d
        d = d[~d.index.duplicated(keep="last")]; d.to_parquet(f)
    print(f"{product}: {f}", flush=True)


if __name__ == "__main__":
    for p in (sys.argv[1:] or PRODUCTS):
        update(p)

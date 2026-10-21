"""Gen277 data (free, public, no account): Bithumb KRW hourly candles for BTC, ETH and the altcoins we have Upbit data for
(a second Korean venue for the kimchi premium). Run on your own PC.

    python -m qpl.live.bithumb

Uses Bithumb's Upbit-style public API (api.bithumb.com/v1/candles/minutes/60, 200 candles per request, paged backwards), paced
well under the public limit; resumable. Output: research_data/more/bithumb_KRW-<COIN>_1h.parquet (same format as the Upbit files)."""
import time
from urllib.parse import quote
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from qpl.live.more_data import get

ROOT = Path(__file__).resolve().parents[3]
MORE = ROOT / "research_data" / "more"
START = datetime(2020, 1, 1, tzinfo=timezone.utc)


def coins():
    return sorted(p.stem.replace("upbit_KRW-", "").replace("_1h", "") for p in MORE.glob("upbit_KRW-*_1h.parquet"))


def fetch(c):
    m = f"KRW-{c}"; f = MORE / f"bithumb_{m}_1h.parquet"
    stop = pd.read_parquet(f).index.max().to_pydatetime().replace(tzinfo=timezone.utc) if f.exists() else START
    to = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0); rows = []
    while to > stop:
        try:
            js = get(f"https://api.bithumb.com/v1/candles/minutes/60?market={m}&count=200&to={quote(f'{to:%Y-%m-%d %H:%M:%S}')}")
        except Exception as e:
            print(f"  {m}: {e.__class__.__name__}: {str(e)[:160]} - stopping here (run again later)", flush=True); break
        if not js or not isinstance(js, list):
            break
        rows += js
        nxt = datetime.fromisoformat(js[-1]["candle_date_time_utc"]).replace(tzinfo=timezone.utc)
        if nxt >= to:
            break
        to = nxt; time.sleep(0.25)
    if rows:
        d = pd.DataFrame(rows); d.index = pd.to_datetime(d["candle_date_time_utc"])
        d = d[["opening_price", "high_price", "low_price", "trade_price", "candle_acc_trade_volume"]].astype("float64")
        d.columns = ["open", "high", "low", "close", "volume"]
        if f.exists():
            d = pd.concat([pd.read_parquet(f), d])
        d = d[~d.index.duplicated(keep="last")].sort_index(); d.to_parquet(f)
        print(f"{m}: {len(d)} rows {d.index.min()} .. {d.index.max()}", flush=True)
    else:
        print(f"{m}: no data (not listed on Bithumb, or the API refused)", flush=True)


if __name__ == "__main__":
    for c in coins():
        fetch(c)

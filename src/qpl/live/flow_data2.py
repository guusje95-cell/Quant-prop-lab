"""Gen247 data (free public endpoints, no account, no key), for two untested information sources:
  - Upbit KRW hourly for the altcoins we trade (kimchi premium per altcoin; BTC/ETH already in research_data/more)
  - Binance SPOT hourly klines with taker-buy volume for the 20 perp coins (spot-led vs perp-led buying)

    python -m qpl.live.flow_data2            # both (resumable; about 30-45 minutes)
    python -m qpl.live.flow_data2 upbit      # one part: upbit | spot

Outputs: research_data/more/upbit_KRW-<COIN>_1h.parquet and research_data/binance_spot/<COIN>USDT_1h.parquet (float32, compact).
Requests are paced well under each venue's public rate limit."""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from qpl.live import binance_public as BP
from qpl.live.more_data import get

ROOT = Path(__file__).resolve().parents[3]
MORE = ROOT / "research_data" / "more"
SPOT_OUT = ROOT / "research_data" / "binance_spot"
COINS = ['AAVE', 'ADA', 'ATOM', 'AVAX', 'BCH', 'BNB', 'BTC', 'DOGE', 'DOT', 'ETC', 'ETH', 'FIL', 'LINK', 'LTC', 'NEAR', 'SOL', 'TRX',
         'UNI', 'XLM', 'XRP']
START = datetime(2020, 1, 1, tzinfo=timezone.utc)


def upbit_alts():
    listed = {m["market"] for m in get("https://api.upbit.com/v1/market/all")}
    for c in COINS:
        m = f"KRW-{c}"
        if c in ("BTC", "ETH") or m not in listed:
            print(f"{m}: {'skip (already have it)' if c in ('BTC', 'ETH') else 'not listed on Upbit'}", flush=True); continue
        f = MORE / f"upbit_{m}_1h.parquet"
        stop = pd.read_parquet(f).index.max().to_pydatetime().replace(tzinfo=timezone.utc) if f.exists() else START
        to = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0); rows = []
        while to > stop:
            js = get(f"https://api.upbit.com/v1/candles/minutes/60?market={m}&count=200&to={to:%Y-%m-%dT%H:%M:%SZ}")
            if not js:
                break
            rows += js; to = datetime.fromisoformat(js[-1]["candle_date_time_utc"]).replace(tzinfo=timezone.utc); time.sleep(0.25)
        if rows:
            d = pd.DataFrame(rows); d.index = pd.to_datetime(d["candle_date_time_utc"])
            d = d[["opening_price", "high_price", "low_price", "trade_price", "candle_acc_trade_volume"]].astype("float64")
            d.columns = ["open", "high", "low", "close", "volume"]
            if f.exists():
                d = pd.concat([pd.read_parquet(f), d])
            d = d[~d.index.duplicated(keep="last")].sort_index(); MORE.mkdir(parents=True, exist_ok=True); d.to_parquet(f)
            print(f"{m}: {len(d)} rows {d.index.min()} .. {d.index.max()}", flush=True)


def spot():
    c = BP.Client(); SPOT_OUT.mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp.now("UTC").tz_localize(None).floor("h")
    for coin in COINS:
        f = SPOT_OUT / f"{coin}USDT_1h.parquet"; old = pd.read_parquet(f) if f.exists() else None
        start = old.index.max() + pd.Timedelta(hours=1) if old is not None else pd.Timestamp("2020-01-01")
        for host in BP.SPOT:
            try:
                k = BP._klines(c, f"{host}/api/v3/klines", f"{coin}USDT", "1h", start, now, limit=1000); break
            except BP.Restricted:
                raise
            except Exception as e:
                print(f"  {coin}: {host} failed ({e.__class__.__name__}), trying the next host", flush=True); k = None
        if k is None or not len(k):
            print(f"{coin}USDT spot: nothing new", flush=True); continue
        k = k[["close", "volume", "quote_volume", "taker_buy_volume", "taker_buy_quote_volume"]].astype("float32")
        d = pd.concat([old, k]) if old is not None else k
        d = d[~d.index.duplicated(keep="last")].sort_index(); d.to_parquet(f)
        print(f"{coin}USDT spot: {len(d)} rows {d.index.min()} .. {d.index.max()}", flush=True)


if __name__ == "__main__":
    part = sys.argv[1] if sys.argv[1:] else "all"
    if part in ("upbit", "all"):
        upbit_alts()
    if part in ("spot", "all"):
        spot()

"""Gen102 data (public endpoints, no account, no key), saved to research_data/more/ and research_data/coinbase/:
  - Coinbase USD hourly for the CFD altcoins (premium on more coins)
  - Upbit KRW hourly BTC/ETH + USD/KRW daily from Yahoo (the 'kimchi' premium: Korean retail demand)
  - Bitstamp USD hourly BTC/ETH (a second US/EU venue, to replicate the Coinbase premium)
  - Crypto Fear & Greed index daily (alternative.me)

    python -m qpl.live.more_data            # everything (resumable; about 30-60 minutes)
    python -m qpl.live.more_data upbit      # one part: coinbase | upbit | bitstamp | fng
Requests are paced well under each venue's public rate limit."""
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from qpl.live import coinbase_public as CB

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "more"
HDR = {"User-Agent": "quant-prop-lab research"}
START = datetime(2020, 1, 1, tzinfo=timezone.utc)


def get(url):
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30) as r:
                return json.loads(r.read())
        except Exception as ex:
            err = ex; time.sleep(2 ** (k + 1))
    raise RuntimeError(f"{url}: {err}")


def save(df, name):
    OUT.mkdir(parents=True, exist_ok=True); f = OUT / f"{name}.parquet"
    if f.exists():
        df = pd.concat([pd.read_parquet(f), df])
    df = df[~df.index.duplicated(keep="last")].sort_index(); df.to_parquet(f)
    print(f"{name}: {len(df)} rows {df.index.min()} .. {df.index.max()} -> {f}", flush=True)


def coinbase_alts():
    for p in ("SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "LINK-USD", "AVAX-USD", "DOT-USD", "LTC-USD", "BCH-USD"):
        try:
            CB.update(p)
        except Exception as e:
            print(p, "FAILED", e, flush=True)


def upbit():
    for m in ("KRW-BTC", "KRW-ETH"):
        rows = []; to = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        f = OUT / f"upbit_{m}_1h.parquet"
        stop = pd.read_parquet(f).index.max().to_pydatetime().replace(tzinfo=timezone.utc) if f.exists() else START
        while to > stop:
            js = get(f"https://api.upbit.com/v1/candles/minutes/60?market={m}&count=200&to={to:%Y-%m-%dT%H:%M:%SZ}")
            if not js:
                break
            rows += js; to = datetime.fromisoformat(js[-1]["candle_date_time_utc"]).replace(tzinfo=timezone.utc)
            time.sleep(0.25)
            if len(rows) % 4000 < 200:
                print(f"  {m} back to {to:%Y-%m-%d}", flush=True)
        if rows:
            d = pd.DataFrame(rows); d.index = pd.to_datetime(d["candle_date_time_utc"])
            save(d[["opening_price", "high_price", "low_price", "trade_price", "candle_acc_trade_volume"]].rename(
                columns={"opening_price": "open", "high_price": "high", "low_price": "low", "trade_price": "close", "candle_acc_trade_volume": "volume"}).astype(float),
                f"upbit_{m}_1h")
    js = get(f"https://query1.finance.yahoo.com/v8/finance/chart/KRW=X?period1=1514764800&period2={int(time.time())}&interval=1d")["chart"]["result"][0]
    d = pd.DataFrame({"close": js["indicators"]["quote"][0]["close"]}, index=pd.to_datetime(js["timestamp"], unit="s")).dropna()
    save(d, "yahoo_USDKRW_1d")


def bitstamp():
    for pair in ("btcusd", "ethusd"):
        f = OUT / f"bitstamp_{pair}_1h.parquet"
        t = int((pd.read_parquet(f).index.max() + pd.Timedelta(hours=1)).timestamp()) if f.exists() else int(START.timestamp())
        now = int(time.time()); rows = []
        while t < now:
            js = get(f"https://www.bitstamp.net/api/v2/ohlc/{pair}/?step=3600&limit=1000&start={t}")
            data = js.get("data", {}).get("ohlc", [])
            if not data:
                t += 1000 * 3600; continue
            rows += data; t = int(data[-1]["timestamp"]) + 3600; time.sleep(0.3)
            if len(rows) % 10000 < 1000:
                print(f"  {pair} up to {pd.Timestamp(t, unit='s'):%Y-%m-%d}", flush=True)
        if rows:
            d = pd.DataFrame(rows); d.index = pd.to_datetime(d["timestamp"].astype(int), unit="s")
            save(d[["open", "high", "low", "close", "volume"]].astype(float), f"bitstamp_{pair}_1h")


def fng():
    js = get("https://api.alternative.me/fng/?limit=0&format=json")["data"]
    d = pd.DataFrame(js); d.index = pd.to_datetime(d["timestamp"].astype(int), unit="s")
    save(d[["value"]].astype(float), "fear_greed_1d")


PARTS = {"coinbase": coinbase_alts, "upbit": upbit, "bitstamp": bitstamp, "fng": fng}

if __name__ == "__main__":
    for name in (sys.argv[1:] or list(PARTS)):
        print(f"== {name} ==", flush=True)
        try:
            PARTS[name]()
        except Exception as e:
            print(name, "FAILED:", e, "(run again later; the others continue)", flush=True)
    print("\nDone. Share it with Claude: git add research_data  -> git commit -m \"more data\" -> git push", flush=True)

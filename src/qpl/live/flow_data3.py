"""Gen262 data (free public endpoints, no account, no key): more regional-demand premia, after the altcoin kimchi sleeve passed (Gen247).
  - Upbit KRW hourly for the 40 extra Binance coins that Upbit lists (a broader altcoin kimchi test)
  - Binance SPOT hourly for local-fiat pairs: BTC / ETH / USDT against TRY, BRL, EUR (Turkish, Brazilian, euro-area demand)
  - Yahoo daily FX: USD/TRY, USD/BRL, EUR/USD

    python -m qpl.live.flow_data3            # everything (resumable; about 30-60 minutes)
    python -m qpl.live.flow_data3 upbit      # one part: upbit | fiat | fx

Outputs: research_data/more/upbit_KRW-<COIN>_1h.parquet, research_data/binance_fiat/<PAIR>_1h.parquet, research_data/more/yahoo_<FX>_1d.parquet."""
import sys
import time
from pathlib import Path

import pandas as pd

from qpl.live import binance_public as BP
from qpl.live import flow_data2 as F2
from qpl.live.more_data import get

ROOT = Path(__file__).resolve().parents[3]
MORE = ROOT / "research_data" / "more"
FIAT = ROOT / "research_data" / "binance_fiat"
EXTRA = sorted({p.name.split("USDT_")[0] for p in (ROOT / "research_data" / "binance_extra").glob("*USDT_1h.parquet")})
PAIRS = ["BTCTRY", "ETHTRY", "USDTTRY", "BTCBRL", "ETHBRL", "USDTBRL", "BTCEUR", "ETHEUR", "EURUSDT"]
FX = {"USDTRY": "TRY=X", "USDBRL": "BRL=X", "EURUSD": "EURUSD=X"}


def upbit_extra():
    F2.COINS = [c.replace("1000", "") for c in EXTRA]                # Upbit lists PEPE / SHIB without the 1000 prefix
    F2.upbit_alts()


def fiat():
    c = BP.Client(); FIAT.mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp.now("UTC").tz_localize(None).floor("h")
    for pair in PAIRS:
        f = FIAT / f"{pair}_1h.parquet"; old = pd.read_parquet(f) if f.exists() else None
        start = old.index.max() + pd.Timedelta(hours=1) if old is not None else pd.Timestamp("2020-01-01")
        k = None
        for host in BP.SPOT:
            try:
                k = BP._klines(c, f"{host}/api/v3/klines", pair, "1h", start, now, limit=1000); break
            except BP.Restricted:
                raise
            except Exception as e:
                print(f"  {pair}: {host} failed ({e.__class__.__name__}), trying the next host", flush=True)
        if k is None or not len(k):
            print(f"{pair}: nothing new", flush=True); continue
        k = k[["close", "volume", "quote_volume", "taker_buy_volume"]].astype("float64")
        d = pd.concat([old, k]) if old is not None else k
        d = d[~d.index.duplicated(keep="last")].sort_index(); d.to_parquet(f)
        print(f"{pair}: {len(d)} rows {d.index.min()} .. {d.index.max()}", flush=True)


def fx():
    for name, sym in FX.items():
        js = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=1514764800&period2={int(time.time())}&interval=1d")["chart"]["result"][0]
        d = pd.DataFrame({"close": js["indicators"]["quote"][0]["close"]}, index=pd.to_datetime(js["timestamp"], unit="s")).dropna()
        f = MORE / f"yahoo_{name}_1d.parquet"
        if f.exists():
            d = pd.concat([pd.read_parquet(f), d])
        d = d[~d.index.duplicated(keep="last")].sort_index(); d.to_parquet(f)
        print(f"{name}: {len(d)} rows {d.index.min()} .. {d.index.max()}", flush=True)


if __name__ == "__main__":
    part = sys.argv[1] if sys.argv[1:] else "all"
    if part in ("upbit", "all"):
        upbit_extra()
    if part in ("fiat", "all"):
        fiat()
    if part in ("fx", "all"):
        fx()

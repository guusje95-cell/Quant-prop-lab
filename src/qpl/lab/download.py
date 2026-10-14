"""Download PUBLIC market data into data/lab/<name>.parquet (long format: time, symbol, open, high, low, close, volume).
No API keys, no accounts. Run on your own PC (Bybit/Binance are geo-blocked from some cloud servers).

  python -m qpl.lab.download bybit   --symbols BTCUSDT ETHUSDT SOLUSDT --interval D --start 2020-01-01
  python -m qpl.lab.download binance --symbols BTCUSDT ETHUSDT --interval 1d --start 2019-01-01 [--futures]
  python -m qpl.lab.download okx     --symbols BTC ETH SOL --interval 1H --start 2020-01-01
  python -m qpl.lab.download yahoo   --symbols ^GSPC ^NDX GC=F EURUSD=X
  python -m qpl.lab.download stablecoins            # USDT+USDC market cap (Coin Metrics community API) for the C* filter
Each run writes one file, e.g. data/lab/bybit_D.parquet, which the Lab app lists as a data source."""
from __future__ import annotations

import argparse
import time

import pandas as pd
import requests

from qpl.lab.data import LAB

HDR = {"User-Agent": "qpl-backtest-lab/1.0 (public market data)"}


def _get(url, params=None, tries=6):
    for k in range(tries):
        try:
            r = requests.get(url, params=params, headers=HDR, timeout=30)
            if r.status_code in (418, 429):
                time.sleep(5 * (k + 1)); continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if k == tries - 1:
                raise RuntimeError(f"{url}: {e}") from e
            time.sleep(2 * (k + 1))


def _ms(ts):
    return int(pd.Timestamp(ts, tz="UTC").timestamp() * 1000)


def bybit(symbol, interval="D", start="2020-01-01", category="linear"):
    """Bybit v5 kline (newest first, max 1000 per call); interval: 1 3 5 15 30 60 120 240 360 720 D W M."""
    rows, end = [], _ms(pd.Timestamp.now('UTC').tz_localize(None))
    s = _ms(start)
    while True:
        d = _get("https://api.bybit.com/v5/market/kline",
                 {"category": category, "symbol": symbol, "interval": interval, "start": s, "end": end, "limit": 1000})
        lst = d.get("result", {}).get("list", [])
        if d.get("retCode") not in (0, None):
            raise RuntimeError(f"Bybit {symbol}: {d.get('retMsg')}")
        if not lst:
            break
        rows += lst
        oldest = int(lst[-1][0])
        if oldest <= s or len(lst) < 1000:
            break
        end = oldest - 1
        time.sleep(0.15)
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume", "turnover"])
    df["time"] = pd.to_datetime(df.pop("t").astype("int64"), unit="ms")
    return df.drop(columns="turnover").astype({k: float for k in ("open", "high", "low", "close", "volume")})


def binance(symbol, interval="1d", start="2019-01-01", futures=False):
    """Binance klines (oldest first, max 1000 per call). futures=True uses USD-M perpetuals."""
    url = "https://fapi.binance.com/fapi/v1/klines" if futures else "https://api.binance.com/api/v3/klines"
    rows, s = [], _ms(start)
    while True:
        d = _get(url, {"symbol": symbol, "interval": interval, "startTime": s, "limit": 1000})
        if not d:
            break
        rows += d
        s = int(d[-1][0]) + 1
        if len(d) < 1000:
            break
        time.sleep(0.15)
    df = pd.DataFrame([r[:6] for r in rows], columns=["t", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df.pop("t").astype("int64"), unit="ms")
    return df.astype({k: float for k in ("open", "high", "low", "close", "volume")})


def okx(symbol, interval="1H", start="2020-01-01"):
    inst = symbol if "-" in symbol else f"{symbol}-USDT-SWAP"
    rows, after, s = [], None, _ms(start)
    while True:
        p = {"instId": inst, "bar": interval, "limit": 100}
        if after:
            p["after"] = after
        d = _get("https://www.okx.com/api/v5/market/history-candles", p).get("data", [])
        if not d:
            break
        rows += d; after = d[-1][0]
        if int(after) <= s:
            break
        time.sleep(0.12)
    df = pd.DataFrame([r[:6] for r in rows if r[8] == "1"], columns=["t", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df.pop("t").astype("int64"), unit="ms")
    df = df.astype({k: float for k in ("open", "high", "low", "close", "volume")})
    return df[df["time"] >= pd.Timestamp(start)]


def yahoo(symbol, start="2000-01-01"):
    p1 = _ms(start) // 1000
    d = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
             {"period1": p1, "period2": int(time.time()), "interval": "1d", "events": "div|split"})["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close", "volume")})
    adj = d["indicators"].get("adjclose")
    if adj:                                          # total-return adjust (dividends/splits)
        f = pd.Series(adj[0]["adjclose"]) / df["close"]
        for k in ("open", "high", "low", "close"):
            df[k] = df[k] * f
    df["time"] = pd.to_datetime(d["timestamp"], unit="s").normalize()
    return df.dropna(subset=["close"])


def stablecoins(start="2018-01-01"):
    d = _get("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
             {"assets": "usdt,usdc", "metrics": "CapMrktCurUSD", "frequency": "1d", "page_size": 10000, "start_time": start})["data"]
    df = pd.DataFrame(d)
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None).dt.normalize()
    s = df.assign(c=df["CapMrktCurUSD"].astype(float)).groupby("time")["c"].sum()
    LAB.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"cap": s}).to_parquet(LAB / "stablecoins.parquet")
    return s


def save(frames: dict, name: str, freq: str):
    out = pd.concat([f.assign(symbol=s) for s, f in frames.items()], ignore_index=True)[["time", "symbol", "open", "high", "low", "close", "volume"]]
    out.attrs["freq"] = freq
    LAB.mkdir(parents=True, exist_ok=True)
    p = LAB / f"{name}.parquet"
    out.to_parquet(p)
    return p


FREQ = {"D": "1d", "1d": "1d", "1D": "1d", "60": "1h", "1h": "1h", "1H": "1h", "240": "4h", "4h": "4h", "4H": "4h"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", choices=["bybit", "binance", "okx", "yahoo", "stablecoins"])
    ap.add_argument("--symbols", nargs="*", default=[])
    ap.add_argument("--interval", default=None)
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--futures", action="store_true", help="binance: USD-M perpetuals instead of spot")
    ap.add_argument("--name", default=None, help="file name in data/lab (default <source>_<interval>)")
    a = ap.parse_args()
    if a.source == "stablecoins":
        s = stablecoins(a.start); print("stablecoins", len(s), s.index.min().date(), s.index.max().date()); return
    iv = a.interval or {"bybit": "D", "binance": "1d", "okx": "1H", "yahoo": "1d"}[a.source]
    frames = {}
    for sym in a.symbols:
        try:
            f = {"bybit": lambda: bybit(sym, iv, a.start), "binance": lambda: binance(sym, iv, a.start, a.futures),
                 "okx": lambda: okx(sym, iv, a.start), "yahoo": lambda: yahoo(sym, a.start)}[a.source]()
            frames[sym] = f
            print(f"{sym}: {len(f)} bars {f['time'].min()} .. {f['time'].max()}", flush=True)
        except Exception as e:
            print(f"{sym}: FAILED {e}", flush=True)
    if frames:
        p = save(frames, a.name or f"{a.source}{'_fut' if a.futures else ''}_{iv}", FREQ.get(iv, "1d"))
        print("saved", p)


if __name__ == "__main__":
    main()

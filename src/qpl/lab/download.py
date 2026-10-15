"""Download PUBLIC market data into data/lab/<name>.parquet (long format: time, symbol, open, high, low, close, volume).
No API keys, no accounts. Run on your own PC (Bybit/Binance are geo-blocked from some cloud servers).

  python -m qpl.lab.download bybit   --symbols BTCUSDT ETHUSDT SOLUSDT --interval D --start 2020-01-01
  python -m qpl.lab.download binance --symbols BTCUSDT ETHUSDT --interval 1d --start 2019-01-01 [--futures]
  python -m qpl.lab.download okx     --symbols BTC ETH SOL --interval 1H --start 2020-01-01
  python -m qpl.lab.download yahoo   --symbols ^GSPC ^NDX GC=F EURUSD=X
  python -m qpl.lab.download yahoo   --symbols NQ=F ES=F --interval 5m        # intraday: 1m = last 7 days, 5m/15m = 60 days, 1h = 2 years
  python -m qpl.lab.download stablecoins            # USDT+USDC market cap (Coin Metrics community API) for the C* filter
  python -m qpl.lab.download dukascopy-github --symbols US100 US500 --interval M5   # index CFD bars 2020-09..2023-09 (M15/H1: longer)
  python -m qpl.lab.download futures-github                # ~30 US futures, daily total-return index 1970s..2024-03 (for pairs)
  python -m qpl.lab.download china --symbols RB0 HC0 I0 J0 JM0  # Chinese dominant futures (needs `pip install akshare`)
  python -m qpl.lab.download topstepx --symbols ES NQ MES MNQ --interval 1min  # REAL CME futures (1min/5min/15min/30min: Jan-Apr 2026; 1h/4h: 2025-03..2026-04)
  python -m qpl.lab.download dukascopy --symbols US100 US500 --start 2013-01-01   # 1-MINUTE index CFDs, free, 2012+ (your PC; ~20 min per symbol per 10 years)
  python -m qpl.lab.download databento --symbols ES NQ --interval 1m --start 2015-01-01 --max-usd 20   # REAL CME 1-minute (free $125 sign-up credit; key in env DATABENTO_API_KEY)
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


YAHOO_MAX_DAYS = {"1m": 7, "5m": 59, "15m": 59, "30m": 59, "1h": 729}     # Yahoo only serves recent intraday history


def yahoo(symbol, start="2000-01-01", interval="1d"):
    p1 = _ms(start) // 1000
    if interval in YAHOO_MAX_DAYS:
        p1 = max(p1, int(time.time()) - YAHOO_MAX_DAYS[interval] * 86400)
    d = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
             {"period1": p1, "period2": int(time.time()), "interval": interval, "events": "div|split"})["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close", "volume")})
    adj = d["indicators"].get("adjclose")
    if adj:                                          # total-return adjust (dividends/splits)
        f = pd.Series(adj[0]["adjclose"]) / df["close"]
        for k in ("open", "high", "low", "close"):
            df[k] = df[k] * f
    t = pd.to_datetime(d["timestamp"], unit="s")
    df["time"] = t.normalize() if interval == "1d" else t
    if interval != "1d":
        df = df[df["time"].dt.second == 0]                    # drop the still-forming last bar
    return df.dropna(subset=["close"])


GH_RAW = "https://raw.githubusercontent.com"
DUKA_GH = (f"{GH_RAW}/TheSnowGuru/Stocks-Futures-Financial-Time-series-Tick-Bar-Data/5fa48d39fd20858d6591db25e6eeee5de45ce6fd/"
           "{path}")
DUKA_FILES = {"US500": "indices/s&p500/USA500IDXUSD_{tf}.csv", "US100": "indices/nasdaq100/USATECHIDXUSD_{tf}.csv",
              "US30": "indices/dow30/USA30IDXUSD_{tf}.csv", "DE40": "indices/dax30/DEUIDXEUR_{tf}.csv",
              "XAUUSD": "commodities/gold/XAUUSD_{tf}.csv", "XAGUSD": "commodities/silver/XAGUSD_{tf}.csv",
              "BRENT": "commodities/brent/BRENTCMDUSD_{tf}.csv", "EURUSD": "forex/eurusd/EURUSD_{tf}.csv",
              "GBPUSD": "forex/gbpusd/GBPUSD_{tf}.csv", "USDJPY": "forex/usdjpy/USDJPY_{tf}.csv",
              "AUDUSD": "forex/audusd/AUDUSD_{tf}.csv", "USDCAD": "forex/usdcad/USDCAD_{tf}.csv", "USDCHF": "forex/usdchf/USDCHF_{tf}.csv"}


def dukascopy_github(symbol, interval="M5"):
    """Dukascopy CFD bars redistributed on GitHub (UTC, tab separated). M5 / M15 files hold the last 200,000 bars
    (M5: 2020-09 -> 2023-09), H1 / D1 go back further."""
    import io
    path = DUKA_FILES[symbol].format(tf=interval).replace("&", "%26")
    r = requests.get(DUKA_GH.format(path=path), headers=HDR, timeout=120); r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), sep="\t")
    df.columns = [c.strip().lower() for c in df.columns]
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M:%S")
    return df[["time", "open", "high", "low", "close", "volume"]]


PYSYS = f"{GH_RAW}/robcarver17/pysystemtrade/master/data/futures"
FUTURES_PAIRS = ["GOLD", "SILVER", "PLAT", "PALLAD", "COPPER", "CRUDE_W", "HEATOIL", "GASOILINE", "GAS_US", "CORN", "WHEAT",
                 "REDWHEAT", "SOYBEAN", "SOYMEAL", "SOYOIL", "SUGAR11", "COFFEE", "COCOA", "COTTON2", "LEANHOG", "LIVECOW", "FEEDCOW",
                 "SP500", "NASDAQ", "DOW", "US10", "US5", "US2", "US20"]


def futures_github(symbol):
    """pysystemtrade (GPL-3) futures: back-adjusted price + current contract price -> roll-free total-return index (close only)."""
    import io
    adj = pd.read_csv(io.StringIO(requests.get(f"{PYSYS}/adjusted_prices_csv/{symbol}.csv", headers=HDR, timeout=120).text),
                      parse_dates=["DATETIME"]).set_index("DATETIME")["price"]
    mp = pd.read_csv(io.StringIO(requests.get(f"{PYSYS}/multiple_prices_csv/{symbol}.csv", headers=HDR, timeout=120).text),
                     parse_dates=["DATETIME"]).set_index("DATETIME")["PRICE"]
    day = lambda s: s.groupby(s.index.normalize()).last()
    adj, mp = day(adj), day(mp).reindex(day(adj).index).ffill()
    r = (adj.diff() / mp.shift(1)).dropna()
    c = 100 * (1 + r).cumprod()
    return pd.DataFrame({"time": c.index, "open": c.values, "high": c.values, "low": c.values, "close": c.values, "volume": float("nan")})


TOPSTEP = f"{GH_RAW}/axb0306/cme-futures-ohlc/main"
def topstepx(symbol, interval="1min"):
    """Real CME Globex futures bars (TopstepX / ProjectX API, redistributed on GitHub: axb0306/cme-futures-ohlc). UTC.
    Symbols include ES NQ YM RTY MES MNQ MYM M2K GC SI MGC CL MCL NG ZN ZB ZF ZT 6E 6B 6J ZC ZS ZW LE HE MBT MET."""
    import io
    import json
    from pathlib import Path
    files = json.loads((Path(__file__).with_name("topstepx_files.json")).read_text())["files"]
    if symbol not in files or interval not in files[symbol]:
        raise KeyError(f"TopstepX has no {symbol} {interval}; available: {sorted(files.get(symbol, {})) or sorted(files)}")
    r = requests.get(f"{TOPSTEP}/{files[symbol][interval]}", headers=HDR, timeout=180); r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df["time"] = pd.to_datetime(df.pop("datetime").str.slice(0, 19))
    return df[["time", "open", "high", "low", "close", "volume"]]


# Dukascopy public datafeed: one LZMA file per day of 1-minute BID candles. 24-byte big-endian records:
# uint32 seconds since 00:00 UTC, int32 open, close, low, high (price x 10^k), float32 volume.
DUKA_SYM = {"US100": "USATECHIDXUSD", "US500": "USA500IDXUSD", "US30": "USA30IDXUSD", "US2000": "USSC2000IDXUSD", "DE40": "DEUIDXEUR",
            "UK100": "GBRIDXGBP", "JP225": "JPNIDXJPY", "EU50": "EUSIDXEUR", "FR40": "FRAIDXEUR", "AUS200": "AUSIDXAUD", "HK50": "HKGIDXHKD",
            "CH20": "CHEIDXCHF", "ES35": "ESPIDXEUR",
            "XAUUSD": "XAUUSD", "XAGUSD": "XAGUSD", "WTI": "LIGHTCMDUSD", "BRENT": "BRENTCMDUSD", "NATGAS": "GASCMDUSD", "COPPER": "COPPERCMDUSD",
            "BUND": "BUNDTREUR", "USTBOND": "USTBONDTRUSD", "BTCUSD": "BTCUSD", "ETHUSD": "ETHUSD",
            "EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY", "AUDUSD": "AUDUSD", "USDCAD": "USDCAD", "USDCHF": "USDCHF",
            "NZDUSD": "NZDUSD", "EURJPY": "EURJPY", "GBPJPY": "GBPJPY", "EURGBP": "EURGBP", "EURCHF": "EURCHF", "AUDJPY": "AUDJPY"}
# plausible price ranges, used to find the price scale 10^k from the data itself (so a wrong guess can never pass silently)
DUKA_RANGE = {"US100": (1000, 60000), "US500": (500, 15000), "US30": (5000, 100000), "US2000": (300, 6000), "DE40": (3000, 60000),
              "UK100": (3000, 20000), "JP225": (8000, 80000), "EU50": (1500, 15000), "FR40": (2500, 20000), "AUS200": (3000, 20000),
              "HK50": (8000, 60000), "CH20": (5000, 30000), "ES35": (4000, 30000),
              "XAUUSD": (200, 10000), "XAGUSD": (3, 200), "WTI": (5, 200), "BRENT": (5, 200), "NATGAS": (0.5, 20), "COPPER": (1, 15),
              "BUND": (100, 250), "USTBOND": (80, 250), "BTCUSD": (500, 500000), "ETHUSD": (50, 50000),
              "EURUSD": (0.5, 2), "GBPUSD": (0.8, 2.5), "USDJPY": (60, 250), "AUDUSD": (0.4, 1.2), "USDCAD": (0.8, 1.8), "USDCHF": (0.5, 1.8),
              "NZDUSD": (0.4, 1.1), "EURJPY": (80, 250), "GBPJPY": (100, 300), "EURGBP": (0.6, 1.1), "EURCHF": (0.8, 1.8), "AUDJPY": (50, 150)}


_DUKA = None
_PACE = {"pause": 1.5, "streak": 0}                                  # adaptive pause between Dukascopy requests


def _pace(ok: bool):
    """Slow down after a block (pause x2, max 20 s), speed up slowly after 40 good requests in a row (min 1.5 s)."""
    if ok:
        _PACE["streak"] += 1
        if _PACE["streak"] >= 40:
            _PACE["pause"] = max(1.5, _PACE["pause"] * 0.8); _PACE["streak"] = 0
    else:
        _PACE["pause"] = min(20.0, _PACE["pause"] * 2); _PACE["streak"] = 0
    time.sleep(_PACE["pause"])


def _duka_get(url):
    global _DUKA
    if _DUKA is None:
        _DUKA = requests.Session(); _DUKA.headers.update(HDR)
    return _DUKA.get(url, timeout=(10, 20))


def _duka_decode(content, base):
    import lzma
    import numpy as np
    raw = lzma.decompress(content)
    a = np.frombuffer(raw[: len(raw) // 24 * 24], dtype=np.dtype([("t", ">u4"), ("o", ">i4"), ("c", ">i4"), ("l", ">i4"), ("h", ">i4"), ("v", ">f4")]))
    return pd.DataFrame({"time": pd.Timestamp(base) + pd.to_timedelta(a["t"].astype("int64"), unit="s"),
                         "open": a["o"].astype(float), "high": a["h"].astype(float), "low": a["l"].astype(float),
                         "close": a["c"].astype(float), "volume": a["v"].astype(float)})


def _duka_fetch(url, base, tries=4):
    """-> DataFrame, None (no data) or 'FAILED: reason'. On a block/timeout it cools down 30/60/90 s before retrying."""
    import lzma
    reason = ""
    for k in range(tries):
        try:
            r = _duka_get(url)
            if r.status_code == 404 or (r.status_code == 200 and not r.content):
                _pace(True); return None
            if r.status_code != 200:
                reason = f"HTTP {r.status_code}"
            else:
                try:
                    out = _duka_decode(r.content, base); _pace(True); return out
                except lzma.LZMAError:
                    reason = f"not a data file ({len(r.content)} bytes)"
        except requests.RequestException as e:
            reason = f"{type(e).__name__}"
            global _DUKA
            _DUKA = None                                           # fresh connection after a network error
        _pace(False)
        if k < tries - 1:
            print(f"[{reason}, waiting {30 * (k + 1)} s]", end="", flush=True)
            time.sleep(30 * (k + 1))
    return f"FAILED: {reason}"


def duka_hourly(symbol, start="2013-01-01", end=None, side="BID"):
    """Hourly candles: ONE request per month (vs ~22 for 1-minute), so 2013-2026 takes ~3 minutes per instrument."""
    inst = DUKA_SYM.get(symbol, symbol); lo_, hi_ = DUKA_RANGE.get(symbol, (1e-9, 1e12))
    end = pd.Timestamp(end or pd.Timestamp.now("UTC").tz_localize(None).normalize())
    print(f"{symbol} {side} hourly from {start} (. = month ok, _ = no data, x = failed): ", end="", flush=True)
    parts, missed = [], 0
    for m0 in pd.date_range(pd.Timestamp(start).replace(day=1), end, freq="MS"):
        x = _duka_fetch(f"https://datafeed.dukascopy.com/datafeed/{inst}/{m0.year}/{m0.month - 1:02d}/{side}_candles_hour_1.bi5", m0)
        if isinstance(x, str):
            missed += 1; print("x", end="", flush=True)
        elif x is not None:
            parts.append(x); print(".", end="", flush=True)
        else:
            print("_", end="", flush=True)
    print(f" ({missed} months failed)" if missed else " done", flush=True)
    if not parts:
        raise RuntimeError(f"no Dukascopy hourly data for {symbol}")
    df = pd.concat(parts, ignore_index=True).drop_duplicates("time").sort_values("time")
    df = df[df["volume"] > 0]
    ref = float(df["close"].median())
    for k in range(0, 8):
        if lo_ <= ref / 10 ** k <= hi_:
            break
    else:
        raise RuntimeError(f"{symbol}: could not determine the price scale (median raw {ref})")
    for c in ("open", "high", "low", "close"):
        df[c] = df[c] / 10 ** k
    return df.reset_index(drop=True)


def _duka_day(inst, day, side="BID", tries=4):
    """One day of 1-minute candles -> DataFrame, None (no trading) or 'FAILED: reason'."""
    url = f"https://datafeed.dukascopy.com/datafeed/{inst}/{day.year}/{day.month - 1:02d}/{day.day:02d}/{side}_candles_min_1.bi5"
    return _duka_fetch(url, day, tries)


def dukascopy(symbol, start="2013-01-01", end=None, pause=0.0, side="BID"):
    """1-minute BID candles from Dukascopy's public datafeed (no account). Run on your own PC (blocked from the research
    cloud). Cached per month in data/lab/cache/dukascopy/<SYM>/ so an interrupted download resumes. Weekend minutes with
    zero volume are dropped. Price scale is detected from the data and checked against a plausible range."""
    import numpy as np
    inst = DUKA_SYM.get(symbol, symbol); lo_, hi_ = DUKA_RANGE.get(symbol, (1e-9, 1e12))
    cache = LAB / "cache" / "dukascopy" / (symbol if side == "BID" else f"{symbol}_{side}"); cache.mkdir(parents=True, exist_ok=True)
    print(f"{symbol} {side}: downloading from {start} (one character per day: . = ok, _ = no trading, x = failed and retried next run)", flush=True)
    end = pd.Timestamp(end or pd.Timestamp.now("UTC").tz_localize(None).normalize() - pd.Timedelta(days=1))
    parts = []
    for m0 in pd.date_range(pd.Timestamp(start).replace(day=1), end, freq="MS"):
        f = cache / f"{m0:%Y-%m}.parquet"
        complete = m0 + pd.offsets.MonthEnd(0) < end
        if f.exists() and complete:
            try:
                parts.append(pd.read_parquet(f)); continue
            except Exception:                                    # cut off mid-write (PC went to sleep): download that month again
                f.unlink(missing_ok=True)
        days = [d for d in pd.date_range(max(m0, pd.Timestamp(start)), min(m0 + pd.offsets.MonthEnd(0), end)) if d.weekday() != 5]
        mon, missed = [], []
        print(f"  {symbol} {side} {m0:%Y-%m} ", end="", flush=True)
        for d in days:
            x = _duka_day(inst, d, side)
            if pause:
                time.sleep(pause)
            if isinstance(x, str):
                missed.append(f"{d.date()} {x}"); print("x", end="", flush=True)
            elif x is not None:
                mon.append(x); print(".", end="", flush=True)
            else:
                print("_", end="", flush=True)
        if mon:
            mdf = pd.concat(mon, ignore_index=True)
            if complete and not missed:
                mdf.to_parquet(f)                                # only fully downloaded months are cached
            parts.append(mdf)
        print(f" {sum(len(x) for x in mon) if mon else 0} minutes"
              + (f"  ({len(missed)} days skipped, retried next run; first: {missed[0]})" if missed else ""), flush=True)
    if not parts:
        raise RuntimeError(f"no Dukascopy data for {symbol}")
    df = pd.concat(parts, ignore_index=True).drop_duplicates("time").sort_values("time")
    df = df[df["volume"] > 0]
    ref = float(df["close"].median())
    for k in range(0, 8):
        if lo_ <= ref / 10 ** k <= hi_:
            break
    else:
        raise RuntimeError(f"{symbol}: could not determine the price scale (median raw {ref})")
    for c in ("open", "high", "low", "close"):
        df[c] = df[c] / 10 ** k
    return df.reset_index(drop=True)


def databento_query(symbol, interval="1m", start="2015-01-01", end=None, roll="v", rank=0, schema=None):
    return dict(dataset="GLBX.MDP3", symbols=[f"{symbol}.{roll}.{rank}"], stype_in="continuous", schema=schema or f"ohlcv-{interval}",
                start=start, end=end or (pd.Timestamp.now("UTC").normalize() - pd.Timedelta(days=1)).strftime("%Y-%m-%d"))


def databento_client():
    import os
    import databento as db
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("set the environment variable DATABENTO_API_KEY first (Windows: setx DATABENTO_API_KEY your_key, then open a new terminal)")
    return db.Historical(key)


def databento(symbol, interval="1m", start="2015-01-01", end=None, max_usd=20.0, roll="v", rank=0, schema=None, client=None):
    """REAL CME Globex data from Databento (GLBX.MDP3), continuous contract (roll='v': by volume, 'c': calendar; rank 0 = front,
    1 = second month, ...). Needs a free Databento account (new accounts get $125 data credit) and `pip install databento`; put the
    key in the environment variable DATABENTO_API_KEY (never in code or chat). The cost is checked FIRST and the download is refused
    if it would exceed --max-usd. Prices are NOT back-adjusted: a small gap appears on roll days (fine for intraday tests)."""
    client = client or databento_client()
    q = databento_query(symbol, interval, start, end, roll, rank, schema)
    cost = float(client.metadata.get_cost(**q))
    print(f"  Databento {q['symbols'][0]} {q['schema']} {q['start']}..{q['end']}: estimated cost ${cost:.2f} (limit ${max_usd:.2f})", flush=True)
    if cost > max_usd:
        raise RuntimeError(f"estimated ${cost:.2f} > --max-usd {max_usd}; shorten the period or raise the limit deliberately")
    df = client.timeseries.get_range(**q).to_df().reset_index()
    df["time"] = pd.to_datetime(df["ts_event"]).dt.tz_localize(None)
    if q["schema"].startswith("ohlcv"):
        return df[["time", "open", "high", "low", "close", "volume"]].astype({k: float for k in ("open", "high", "low", "close", "volume")})
    return df


def china(symbol):
    """Chinese dominant continuous futures (e.g. RB0 = rebar) via the free AkShare library (Sina data); install with
    `pip install akshare`. Prices are the unadjusted dominant contract, like the paper's JoinQuant '8888' series."""
    import akshare as ak
    df = ak.futures_main_sina(symbol=symbol)
    df = df.rename(columns={"日期": "time", "开盘价": "open", "最高价": "high", "最低价": "low", "收盘价": "close", "成交量": "volume"})
    df["time"] = pd.to_datetime(df["time"])
    return df[["time", "open", "high", "low", "close", "volume"]].astype({k: float for k in ("open", "high", "low", "close", "volume")})


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


FREQ = {"D": "1d", "1d": "1d", "1D": "1d", "60": "1h", "1h": "1h", "1H": "1h", "240": "4h", "4h": "4h", "4H": "4h",
        "1": "1m", "1m": "1m", "5": "5m", "5m": "5m", "15": "15m", "15m": "15m", "30": "30m", "30m": "30m",
        "M5": "5m", "M15": "15m", "M30": "30m", "H1": "1h", "D1": "1d", "1min": "1m", "5min": "5m", "15min": "15m",
        "30min": "30m", "daily": "1d"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", choices=["bybit", "binance", "okx", "yahoo", "stablecoins", "dukascopy-github", "futures-github", "china",
                                           "topstepx", "dukascopy", "databento"])
    ap.add_argument("--max-usd", type=float, default=20.0, help="databento: refuse downloads estimated above this cost")
    ap.add_argument("--symbols", nargs="*", default=[])
    ap.add_argument("--interval", default=None)
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--futures", action="store_true", help="binance: USD-M perpetuals instead of spot")
    ap.add_argument("--name", default=None, help="file name in data/lab (default <source>_<interval>)")
    a = ap.parse_args()
    if a.source == "stablecoins":
        s = stablecoins(a.start); print("stablecoins", len(s), s.index.min().date(), s.index.max().date()); return
    iv = a.interval or {"bybit": "D", "binance": "1d", "okx": "1H", "yahoo": "1d", "dukascopy-github": "M5", "topstepx": "1min", "dukascopy": "1m",
                                       "databento": "1m"}.get(a.source, "1d")
    if a.source == "futures-github" and not a.symbols:
        a.symbols = FUTURES_PAIRS
    frames = {}
    for sym in a.symbols:
        try:
            f = {"bybit": lambda: bybit(sym, iv, a.start), "binance": lambda: binance(sym, iv, a.start, a.futures),
                 "okx": lambda: okx(sym, iv, a.start), "yahoo": lambda: yahoo(sym, a.start, iv),
                 "dukascopy-github": lambda: dukascopy_github(sym, iv), "futures-github": lambda: futures_github(sym),
                 "topstepx": lambda: topstepx(sym, iv), "dukascopy": lambda: dukascopy(sym, a.start),
                 "databento": lambda: databento(sym, iv, a.start, max_usd=a.max_usd),
                 "china": lambda: china(sym)}[a.source]()
            frames[sym] = f
            print(f"{sym}: {len(f)} bars {f['time'].min()} .. {f['time'].max()}", flush=True)
        except Exception as e:
            print(f"{sym}: FAILED {e}", flush=True)
    if frames:
        default = {"futures-github": "futures_daily", "china": "china_futures_daily",
                   "dukascopy-github": f"dukascopy_{'_'.join(frames)}_{iv}",
                   "topstepx": f"cme_{'_'.join(frames)}_{iv}", "dukascopy": f"dukascopy_{'_'.join(frames)}_1m",
                   "databento": f"databento_{'_'.join(frames)}_{iv}"}.get(a.source, f"{a.source}{'_fut' if a.futures else ''}_{iv}")
        p = save(frames, a.name or default, FREQ.get(iv, "1d"))
        print("saved", p)


if __name__ == "__main__":
    main()

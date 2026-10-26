"""Public Binance market data for paper trading (read-only, no API key, never places orders).

Fetches only what the v5 sleeves read, in the same file formats as the research pack (research_data/binance), into a separate
live folder that the loaders overlay on the pack (QPL_LIVE_PACK):
  <SYM>USDT_5m.parquet        USD-M perp 5-minute klines (only bars that have closed)
  <SYM>USDT_funding.parquet   funding settlements
  <SYM>USDT_premium_1h.parquet hourly premium index klines
  <SYM>USDT_metrics.parquet   5-minute open interest (Binance keeps only the last 30 days on this endpoint)
  binance_spot_majors_1d.parquet  spot daily bars of the 10 majors (C* signal)
Rate limits are respected (small pause between calls, back-off on 429/418). If Binance refuses your location (HTTP 451/403
'restricted location'), the tool stops: do not route around it with a VPN; use the data your jurisdiction allows.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

FAPI = "https://fapi.binance.com"
SPOT = ("https://data-api.binance.vision", "https://api.binance.com")      # official public market-data hosts
KCOLS = ["open", "high", "low", "close", "volume", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume"]
MCOLS = ["sum_open_interest", "sum_open_interest_value", "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
         "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]
SPOT_COLS = ["open", "high", "low", "close", "volume"]


class Restricted(RuntimeError):
    pass


class Client:
    def __init__(self, pause: float = 0.25, timeout: float = 20.0):
        self.s = requests.Session(); self.s.headers["User-Agent"] = "qpl-paper/1.0"; self.pause = pause; self.timeout = timeout

    def get(self, url: str, params: dict):
        for attempt in range(5):
            try:
                r = self.s.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as e:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt); continue
            if r.status_code in (418, 429):                      # rate limited: back off as Binance asks
                time.sleep(int(r.headers.get("Retry-After", 60))); continue
            if r.status_code in (403, 451) or "restricted location" in r.text:
                raise Restricted(f"Binance refused the request from this location ({r.status_code}). Not bypassing it.")
            if r.status_code >= 500:
                time.sleep(2 ** attempt); continue
            r.raise_for_status()
            time.sleep(self.pause)
            return r.json()
        raise RuntimeError(f"giving up on {url}")


def _ms(t: pd.Timestamp) -> int:
    return int(pd.Timestamp(t).value // 1_000_000)


def _klines(c: Client, url: str, symbol: str, interval: str, start: pd.Timestamp, now: pd.Timestamp, limit: int = 1500) -> pd.DataFrame:
    rows, t = [], _ms(start)
    while True:
        d = c.get(url, {"symbol": symbol, "interval": interval, "startTime": t, "limit": limit})
        if not d:
            break
        rows += [x for x in d if x[6] < _ms(now)]                 # closeTime before now: completed bars only
        if len(d) < limit or d[-1][6] >= _ms(now):
            break
        t = d[-1][0] + 1
    if not rows:
        return pd.DataFrame(columns=KCOLS)
    a = np.array([[x[0], *x[1:6], x[7], x[8], x[9], x[10]] for x in rows], dtype="float64")
    df = pd.DataFrame(a[:, 1:], columns=KCOLS, index=pd.DatetimeIndex(pd.to_datetime(a[:, 0].astype("int64"), unit="ms"), name="time"))
    return df[~df.index.duplicated(keep="last")]


def _append(path: Path, new: pd.DataFrame, key: str | None = None):
    """Append rows to a live parquet (index or `key` column = time), newer rows replace older ones."""
    if new is None or len(new) == 0:
        return 0
    if path.exists():
        old = pd.read_parquet(path)
        both = pd.concat([old, new])
    else:
        both = new
    if key:
        both = both.drop_duplicates(key, keep="last").sort_values(key).reset_index(drop=True)
    else:
        both = both[~both.index.duplicated(keep="last")].sort_index()
    tmp = path.with_suffix(".tmp"); both.to_parquet(tmp); tmp.replace(path)
    return len(new)


def _last_time(pack: Path, live: Path, name: str, key: str | None) -> pd.Timestamp | None:
    best = None
    for p in (pack / name, live / name):
        if not p.exists():
            continue
        if key:
            t = pd.to_datetime(pd.read_parquet(p, columns=[key])[key]).max()
        else:
            t = pd.DatetimeIndex(pd.read_parquet(p, columns=["close"]).index).max()
        best = t if best is None or t > best else best
    return best


def update(pack: Path, live: Path, coins: list[str], majors: list[str], now: pd.Timestamp | None = None, log=print,
           spot_base: Path | None = None) -> dict:
    """Bring the live folder up to `now` (UTC, default: current time). Returns counts of new rows per file kind."""
    live.mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp.now("UTC").tz_localize(None) if now is None else pd.Timestamp(now)
    c = Client(); n = {"5m": 0, "funding": 0, "premium": 0, "oi": 0, "spot": 0}
    for coin in coins:
        sym = f"{coin}USDT"
        last = _last_time(pack, live, f"{sym}_5m.parquet", None)
        start = (last + pd.Timedelta(minutes=5)) if last is not None else now - pd.Timedelta(days=60)
        k = _klines(c, f"{FAPI}/fapi/v1/klines", sym, "5m", start, now).astype("float32")
        n["5m"] += _append(live / f"{sym}_5m.parquet", k)

        last = _last_time(pack, live, f"{sym}_funding.parquet", "time")
        start = (last + pd.Timedelta(minutes=1)) if last is not None else now - pd.Timedelta(days=60)
        d = c.get(f"{FAPI}/fapi/v1/fundingRate", {"symbol": sym, "startTime": _ms(start), "limit": 1000})
        if d:
            f = pd.DataFrame({"funding_interval_hours": 8, "last_funding_rate": [float(x["fundingRate"]) for x in d],
                              "time": pd.to_datetime([int(x["fundingTime"]) for x in d], unit="ms")})
            n["funding"] += _append(live / f"{sym}_funding.parquet", f[f.time <= now], key="time")

        last = _last_time(pack, live, f"{sym}_premium_1h.parquet", "time")
        start = (last + pd.Timedelta(hours=1)) if last is not None else now - pd.Timedelta(days=60)
        p = _klines(c, f"{FAPI}/fapi/v1/premiumIndexKlines", sym, "1h", start, now)
        if len(p):
            p = p.reset_index().rename(columns={"index": "time"})
            n["premium"] += _append(live / f"{sym}_premium_1h.parquet", p, key="time")

        last = _last_time(pack, live, f"{sym}_metrics.parquet", "time")
        start = max(last + pd.Timedelta(minutes=5) if last is not None else now - pd.Timedelta(days=29), now - pd.Timedelta(days=29))
        rows, t = [], _ms(start)
        while t < _ms(now):
            d = c.get(f"{FAPI}/futures/data/openInterestHist", {"symbol": sym, "period": "5m", "startTime": t, "limit": 500})
            if not d:
                break
            rows += d
            if len(d) < 500:
                break
            t = int(d[-1]["timestamp"]) + 1
        if rows:
            m = pd.DataFrame({"sum_open_interest": [float(x["sumOpenInterest"]) for x in rows],
                              "sum_open_interest_value": [float(x["sumOpenInterestValue"]) for x in rows]})
            for col in MCOLS[2:]:
                m[col] = np.nan                                   # not used by v5
            m["time"] = pd.to_datetime([int(x["timestamp"]) for x in rows], unit="ms")
            n["oi"] += _append(live / f"{sym}_metrics.parquet", m[m.time <= now], key="time")
        log(f"  {coin}: data up to date")
    # spot daily bars for C*: the research file (data/processed/crypto, not in git) is created from Binance's full history on
    # the first run; afterwards only the last 30 days are refreshed into the live folder
    base = spot_base if spot_base is not None else None
    first = base is not None and not base.exists()
    spot_file = base if first else live / "binance_spot_majors_1d.parquet"
    since = pd.Timestamp("2017-08-01") if first else now - pd.Timedelta(days=30)
    frames = {}
    for coin in majors:
        k = None
        for host in SPOT:
            try:
                k = _klines(c, f"{host}/api/v3/klines", f"{coin}USDT", "1d", since, now, limit=1000)
                break
            except Restricted:
                k = None
        if k is None or not len(k):
            continue
        frames[coin] = k[SPOT_COLS]
    if frames:
        df = pd.concat(frames, axis=1); df.index.name = "t"
        spot_file.parent.mkdir(parents=True, exist_ok=True)
        n["spot"] += _append(spot_file, df)
        if first:
            log(f"  spot daily history created: {spot_file} ({len(df)} days)")
    return n


def stablecoins(log=print):
    """USDT+USDC caps for the C* filter (Coin Metrics community API, as in the research download): full history from 2018
    (data/lab/stablecoins.parquet, not in git), refreshed every run."""
    try:
        from qpl.lab import download as DL
        s = DL.stablecoins("2018-01-01"); log(f"  stablecoins up to {s.index.max().date()}")
        return True
    except Exception as e:                                       # filter falls back to neutral (x1.0) if unavailable
        log(f"  stablecoins: not updated ({e.__class__.__name__}); C* filter will be neutral for missing days")
        return False


RATIO_ENDPOINTS = {"count_toptrader_long_short_ratio": ("topLongShortAccountRatio", "longShortRatio"),
                   "sum_toptrader_long_short_ratio": ("topLongShortPositionRatio", "longShortRatio"),
                   "count_long_short_ratio": ("globalLongShortAccountRatio", "longShortRatio"),
                   "sum_taker_long_short_vol_ratio": ("takerlongshortRatio", "buySellRatio")}


def update_ratios(live: Path, coins: list[str], now: pd.Timestamp | None = None, log=print) -> int:
    """v9.5 (relative crowding, basket): 5-minute long/short and taker ratios (the research pack's metrics columns) into
    <live>/<SYM>USDT_ratios.parquet; binance_pack.metrics fills its NaN ratio columns from it. Binance serves the last 30 days."""
    live.mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp.now("UTC").tz_localize(None) if now is None else pd.Timestamp(now)
    c = Client(); total = 0
    for coin in coins:
        sym = f"{coin}USDT"; f = live / f"{sym}_ratios.parquet"
        last = pd.DatetimeIndex(pd.read_parquet(f).index).max() if f.exists() else None
        start = max(last - pd.Timedelta(minutes=30) if last is not None else now - pd.Timedelta(days=29), now - pd.Timedelta(days=29))
        cols = {}
        for col, (ep, field) in RATIO_ENDPOINTS.items():
            rows, t0 = [], _ms(start)
            while t0 < _ms(now):
                d = c.get(f"{FAPI}/futures/data/{ep}", {"symbol": sym, "period": "5m", "startTime": t0, "limit": 500})
                if not d:
                    break
                rows += d
                if len(d) < 500:
                    break
                t0 = int(d[-1]["timestamp"]) + 1
            if rows:
                cols[col] = pd.Series([float(x[field]) for x in rows], index=pd.to_datetime([int(x["timestamp"]) for x in rows], unit="ms"))
        if cols:
            df = pd.DataFrame(cols); df = df[df.index <= now]; df.index.name = "time"
            total += _append(f, df)
    log(f"  long/short ratios: {total} new rows")
    return total


def update_extra(pack: Path, live: Path, coins: list[str], now: pd.Timestamp | None = None, log=print) -> dict:
    """Extra coins (Gen80 breadth, research_data/binance_extra format): hourly klines, funding, hourly premium index, into live/."""
    live.mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp.now("UTC").tz_localize(None) if now is None else pd.Timestamp(now)
    c = Client(); n = {"1h": 0, "funding": 0, "premium": 0}
    for coin in coins:
        sym = f"{coin}USDT"
        last = _last_time(pack, live, f"{sym}_1h.parquet", None)
        start = (last + pd.Timedelta(hours=1)) if last is not None else now - pd.Timedelta(days=60)
        k = _klines(c, f"{FAPI}/fapi/v1/klines", sym, "1h", start, now)[["open", "high", "low", "close", "volume", "quote_volume"]].astype("float32")
        n["1h"] += _append(live / f"{sym}_1h.parquet", k)
        last = _last_time(pack, live, f"{sym}_funding.parquet", "time")
        start = (last + pd.Timedelta(minutes=1)) if last is not None else now - pd.Timedelta(days=60)
        d = c.get(f"{FAPI}/fapi/v1/fundingRate", {"symbol": sym, "startTime": _ms(start), "limit": 1000})
        if d:
            f = pd.DataFrame({"funding_interval_hours": 8, "last_funding_rate": [float(x["fundingRate"]) for x in d],
                              "time": pd.to_datetime([int(x["fundingTime"]) for x in d], unit="ms")})
            n["funding"] += _append(live / f"{sym}_funding.parquet", f[f.time <= now], key="time")
        last = _last_time(pack, live, f"{sym}_premium_1h.parquet", "time")
        start = (last + pd.Timedelta(hours=1)) if last is not None else now - pd.Timedelta(days=60)
        p = _klines(c, f"{FAPI}/fapi/v1/premiumIndexKlines", sym, "1h", start, now)
        if len(p):
            p = p.reset_index().rename(columns={"index": "time"})
            n["premium"] += _append(live / f"{sym}_premium_1h.parquet", p, key="time")
    log(f"  {len(coins)} extra coins: data up to date")
    return n

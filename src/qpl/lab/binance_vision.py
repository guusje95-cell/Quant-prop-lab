"""Free bulk Binance USD-M futures data from data.binance.vision (no account, no API key). Run on your own PC (the research
cloud cannot reach the site).

    python -m qpl.lab.binance_vision klines  --symbols BTCUSDT ETHUSDT --start 2020-01 --interval 1m
    python -m qpl.lab.binance_vision metrics --symbols BTCUSDT ETHUSDT --start 2021-12-01
    python -m qpl.lab.binance_vision funding --symbols BTCUSDT ETHUSDT --start 2020-01
    python -m qpl.lab.binance_vision premium                   # hourly perp premium index (basis) for the 20 coins, small
    python -m qpl.lab.binance_vision all                       # the 20-coin research set, everything (takes a while)

What you get (all in data/lab/binance_vision/, one parquet per symbol, resumable: finished months are cached):
  klines  : 1-minute OHLCV + number of trades + taker-buy volume (monthly zip files, 2019-09+ for BTC)
  metrics : 5-minute open interest, top-trader and all-account long/short ratios, taker buy/sell ratio (daily zip files, ~2021-12+)
  funding : funding rate every 8h (monthly zip files)
  premium : hourly premium-index klines (perp vs spot index, i.e. the basis; monthly zip files)
Then `python -m qpl.lab.binance_vision build` (run automatically after `all`) writes a compact research pack to
research_data/binance/ (5-minute bars + metrics + funding, ~20-40 MB per coin: commit and push it so Claude can use it) and Lab data sources: data/lab/binance_futures_5m.parquet (resampled from 1m)
and data/lab/binance_futures_1h.parquet, which appear in the app as 'Downloaded: ...'."""
from __future__ import annotations

import argparse
import io
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

from qpl.lab.data import LAB, ROOT

BASE = "https://data.binance.vision/data/futures/um"
OUT = LAB / "binance_vision"
HDR = {"User-Agent": "qpl-backtest-lab/1.0 (public market data)"}
RESEARCH_SET = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
                "LTCUSDT", "BCHUSDT", "TRXUSDT", "ETCUSDT", "XLMUSDT", "ATOMUSDT", "NEARUSDT", "FILUSDT", "UNIUSDT", "AAVEUSDT"]
KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count", "taker_buy_volume",
         "taker_buy_quote_volume", "ignore"]


def _zip_csv(url: str, tries: int = 5) -> pd.DataFrame | None:
    for k in range(tries):
        try:
            r = requests.get(url, headers=HDR, timeout=120)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    raw = f.read().decode()
            first = raw.split("\n", 1)[0]
            has_header = not first.split(",")[0].strip().lstrip("-").isdigit()
            return pd.read_csv(io.StringIO(raw), header=0 if has_header else None)
        except (requests.RequestException, zipfile.BadZipFile):
            time.sleep(3 * (k + 1))
    raise RuntimeError(f"failed: {url}")


def _read_ok(p: Path):
    """A month file cut off mid-write (PC went to sleep) is deleted, so the next run downloads that month again."""
    try:
        return pd.read_parquet(p)
    except Exception:
        print(f"  damaged cache file removed: {p.name} (will be downloaded again next run)")
        p.unlink(missing_ok=True)
        return None


def _months(start: str, end: str | None = None):
    end = pd.Timestamp(end) if end else pd.Timestamp.now("UTC").tz_localize(None) - pd.offsets.MonthBegin(1)
    return pd.date_range(pd.Timestamp(start).replace(day=1), end, freq="MS")


def klines(symbol: str, start: str = "2020-01", interval: str = "1m", kind: str = "klines") -> Path:
    """kind: 'klines' (traded prices) or 'premiumIndexKlines' (perp premium vs the spot index = the basis, used by the funding formula)."""
    tag = interval if kind == "klines" else f"premium_{interval}"
    cache = OUT / "cache" / f"{symbol}_{tag}"; cache.mkdir(parents=True, exist_ok=True)
    for m in _months(start):
        f = cache / f"{m:%Y-%m}.parquet"
        if f.exists() and _read_ok(f) is not None:
            continue
        df = _zip_csv(f"{BASE}/monthly/{kind}/{symbol}/{interval}/{symbol}-{interval}-{m:%Y-%m}.zip")
        if df is None:
            continue
        df.columns = KCOLS[: df.shape[1]]
        ts = pd.to_numeric(df["open_time"])
        df["time"] = pd.to_datetime(ts, unit="us" if ts.max() > 1e14 else "ms")       # 2025+ files use microseconds
        keep = ["time", "open", "high", "low", "close", "volume", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume"]
        df[keep].astype({c: float for c in keep if c != "time"}).to_parquet(f)
        print(f"  {symbol} {tag} {m:%Y-%m}: {len(df)} bars", flush=True)
        time.sleep(0.2)
    parts = [_read_ok(p) for p in sorted(cache.glob("*.parquet"))]
    parts = [p for p in parts if p is not None]
    out = OUT / f"{symbol}_{tag}.parquet"
    if parts:
        pd.concat(parts).drop_duplicates("time").sort_values("time").to_parquet(out)
    return out


def metrics(symbol: str, start: str = "2021-12-01") -> Path:
    cache = OUT / "cache" / f"{symbol}_metrics"; cache.mkdir(parents=True, exist_ok=True)
    for m in _months(start):
        f = cache / f"{m:%Y-%m}.parquet"
        if f.exists() and _read_ok(f) is not None:
            continue
        days = pd.date_range(max(m, pd.Timestamp(start)), m + pd.offsets.MonthEnd(0))
        rows = []
        for d in days:
            if d >= pd.Timestamp.now("UTC").tz_localize(None).normalize():
                break
            df = _zip_csv(f"{BASE}/daily/metrics/{symbol}/{symbol}-metrics-{d:%Y-%m-%d}.zip")
            if df is not None:
                rows.append(df)
            time.sleep(0.1)
        if rows:
            df = pd.concat(rows)
            df["time"] = pd.to_datetime(df["create_time"])
            df.drop(columns=[c for c in ("create_time", "symbol") if c in df]).to_parquet(f)
            print(f"  {symbol} metrics {m:%Y-%m}: {len(df)} rows", flush=True)
    parts = [x for x in (_read_ok(p) for p in sorted(cache.glob("*.parquet"))) if x is not None]
    out = OUT / f"{symbol}_metrics.parquet"
    if parts:
        pd.concat(parts).drop_duplicates("time").sort_values("time").to_parquet(out)
    return out


def funding(symbol: str, start: str = "2020-01") -> Path:
    rows = []
    for m in _months(start):
        df = _zip_csv(f"{BASE}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{m:%Y-%m}.zip")
        if df is not None:
            df.columns = ["calc_time", "funding_interval_hours", "last_funding_rate"][: df.shape[1]]
            rows.append(df); time.sleep(0.1)
    out = OUT / f"{symbol}_funding.parquet"
    if rows:
        df = pd.concat(rows)
        ts = pd.to_numeric(df["calc_time"]); df["time"] = pd.to_datetime(ts, unit="us" if ts.max() > 1e14 else "ms")
        df.drop(columns="calc_time").sort_values("time").to_parquet(out)
        print(f"  {symbol} funding: {len(df)} rows", flush=True)
    return out


def build():
    """Resample the downloaded 1-minute files into Lab data sources (5-minute and hourly, long format)."""
    from qpl.lab import download as DL
    frames5, frames60 = {}, {}
    for p in sorted(OUT.glob("*_1m.parquet")):
        sym = p.stem.replace("_1m", "").replace("USDT", "")
        d = pd.read_parquet(p).set_index("time")
        agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        for rule, store in (("5min", frames5), ("1h", frames60)):
            r = d[list(agg)].resample(rule).agg(agg).dropna(subset=["close"]).reset_index()
            store[sym] = r
    if frames5:
        print(DL.save(frames5, "binance_futures_5m", "5m")); print(DL.save(frames60, "binance_futures_1h", "1h"))
    # compact research pack: one small file per coin (5-min bars incl. trade counts / taker volume, + metrics + funding)
    pack = ROOT / "research_data" / "binance"; pack.mkdir(parents=True, exist_ok=True)
    for p in sorted(OUT.glob("*_1m.parquet")):
        sym = p.stem.replace("_1m", "")
        d = pd.read_parquet(p).set_index("time")
        agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "quote_volume": "sum", "count": "sum",
               "taker_buy_volume": "sum", "taker_buy_quote_volume": "sum"}
        d[[c for c in agg if c in d]].resample("5min").agg({k: v for k, v in agg.items() if k in d}).dropna(subset=["close"]).astype("float32") \
            .to_parquet(pack / f"{sym}_5m.parquet", compression="zstd")
        for extra in ("metrics", "funding", "premium_1h"):
            f = OUT / f"{sym}_{extra}.parquet"
            if f.exists():
                pd.read_parquet(f).to_parquet(pack / f"{sym}_{extra}.parquet", compression="zstd")
    print("research pack ->", pack, "(commit this folder: git add research_data && git commit && git push)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["klines", "metrics", "funding", "premium", "all", "build"])
    ap.add_argument("--symbols", nargs="*", default=RESEARCH_SET)
    ap.add_argument("--start", default=None)
    ap.add_argument("--interval", default="1m")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.what == "build":
        build(); return
    for s in a.symbols:
        try:
            if a.what in ("klines", "all"):
                print(s, "->", klines(s, a.start or "2020-01", a.interval))
            if a.what in ("metrics", "all"):
                print(s, "->", metrics(s, a.start or "2021-12-01"))
            if a.what in ("funding", "all"):
                print(s, "->", funding(s, a.start or "2020-01"))
            if a.what in ("premium", "all"):
                print(s, "->", klines(s, a.start or "2020-01", "1h", kind="premiumIndexKlines"))
        except Exception as e:
            print(s, "FAILED:", e)
    if a.what in ("klines", "premium", "all"):
        build()


if __name__ == "__main__":
    main()

"""One-time data setup for the Backtest Lab on your own PC (all public data, no keys):

    python -m qpl.lab.setup_data            # crypto majors daily + hourly, stablecoin supply, a Yahoo starter set,
                                            # Nasdaq-100 / S&P 500 intraday (MaxAI strategy), US futures daily (pairs strategy)
    python -m qpl.lab.setup_data --quick    # daily crypto + stablecoins only

Tries Binance spot first (history from 2017), then Bybit, then the GitHub mirror of Binance candles (works everywhere).
Writes data/lab/*.parquet; the app lists each file as a data source."""
from __future__ import annotations

import argparse

import pandas as pd
import requests

from qpl.lab import download as DL

MAJORS = ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "AVAX", "DOT", "LINK"]
YAHOO = ["^GSPC", "^NDX", "^DJI", "^GDAXI", "GC=F", "CL=F", "EURUSD=X", "GBPUSD=X", "JPY=X", "BTC-USD", "ETH-USD"]


def github_mirror(sym, interval):
    """Binance spot candles mirrored on GitHub (github.com/finom/static-klines): yearly (1d) / monthly (1h) JSON files."""
    base = f"https://raw.githubusercontent.com/finom/static-klines/main/.klines-cache/{sym}USDT/{interval}"
    rows = []
    if interval == "1d":
        files = [f"{y}-01-01.json" for y in range(2017, pd.Timestamp.now('UTC').year + 1)]
    else:
        files = [f"{d:%Y-%m}-01.json" for d in pd.date_range("2022-01-01", pd.Timestamp.now('UTC').tz_localize(None), freq="MS")]
    for f in files:
        r = requests.get(f"{base}/{f}", timeout=30)
        if r.status_code == 200 and r.text.strip():
            rows += r.json()
    df = pd.DataFrame([x[:6] for x in rows], columns=["t", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df.pop("t").astype("int64"), unit="ms")
    return df.astype({k: float for k in ("open", "high", "low", "close", "volume")}).drop_duplicates("time")


def crypto(interval):
    frames, used = {}, None
    for name, fn in (("binance", lambda s: DL.binance(f"{s}USDT", interval, "2017-08-01")),
                     ("bybit", lambda s: DL.bybit(f"{s}USDT", {"1d": "D", "1h": "60"}[interval], "2018-01-01", "spot")),
                     ("github-mirror", lambda s: github_mirror(s, interval))):
        try:
            frames = {s: fn(s) for s in MAJORS}
            used = name
            break
        except Exception as e:
            print(f"  {name} not available here ({str(e)[:80]}); trying next source")
    if frames:
        p = DL.save(frames, f"crypto_majors_{interval}", interval)
        print(f"crypto majors {interval}: {used} -> {p}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true")
    ap.add_argument("--papers", action="store_true", help="only the data for the two paper strategies"); a = ap.parse_args()
    if a.papers:
        papers(); return
    crypto("1d")
    try:
        s = DL.stablecoins("2017-01-01"); print("stablecoin supply:", len(s), "days")
    except Exception as e:
        print("stablecoin supply not available:", e)
    if a.quick:
        return
    crypto("1h")
    frames = {}
    for s in YAHOO:
        try:
            frames[s] = DL.yahoo(s, "2000-01-01")
        except Exception as e:
            print("yahoo", s, "failed:", e)
    if frames:
        print("yahoo:", DL.save(frames, "yahoo_starter_1d", "1d"))
    papers()


def papers():
    """Data for the two paper strategies: index CFD intraday bars (MaxAI) and a daily futures panel (Kalman pairs)."""
    try:
        print("13 CFDs hourly:", DL.save({s: DL.dukascopy_github(s, "H1") for s in DL.DUKA_FILES}, "dukascopy13_1h", "1h"))
    except Exception as e:
        print("13 CFDs hourly not available:", e)
    try:
        from qpl.lab import futures_curve as FC
        R, _, _ = FC.build(); print("commodity futures curves:", R.shape[1] // 3, "commodities ->", FC.CACHE)
    except Exception as e:
        print("futures curves not available:", e)
    for tf in ("M5", "M15"):
        try:
            print(f"Nasdaq-100 / S&P 500 {tf}:", DL.save({s: DL.dukascopy_github(s, tf) for s in ("US100", "US500")}, f"index_cfd_{tf}", DL.FREQ[tf]))
        except Exception as e:
            print(f"index CFD {tf} not available:", e)
    try:
        print("NQ futures 5m, last 60 days:", DL.save({"NQ": DL.yahoo("NQ=F", "2000-01-01", "5m")}, "nq_futures_5m_recent", "5m"))
        print("NQ futures 1h, last 2 years:", DL.save({"NQ": DL.yahoo("NQ=F", "2000-01-01", "1h")}, "nq_futures_1h_recent", "1h"))
    except Exception as e:
        print("Yahoo NQ intraday not available:", e)
    for iv, syms in (("1min", ("ES", "NQ", "MES", "MNQ", "YM", "RTY", "GC", "CL")), ("5min", ("ES", "NQ", "MES", "MNQ", "YM", "RTY", "GC", "CL")),
                     ("1h", ("ES", "NQ", "YM", "RTY", "GC", "SI", "CL", "NG", "ZN", "6E", "6J", "6B"))):
        try:
            print(f"CME futures {iv} (TopstepX):", DL.save({s: DL.topstepx(s, iv) for s in syms}, f"cme_futures_{iv}", DL.FREQ[iv]))
        except Exception as e:
            print(f"CME futures {iv} not available:", e)
    frames = {}
    for s in DL.FUTURES_PAIRS:
        try:
            frames[s] = DL.futures_github(s)
        except Exception as e:
            print("futures", s, "failed:", e)
    if frames:
        print("US futures daily:", DL.save(frames, "futures_daily", "1d"))


if __name__ == "__main__":
    main()

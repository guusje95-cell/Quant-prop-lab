"""Yahoo Finance public chart API (no key): daily OHLC + adjusted close. Saved to data/raw/yahoo/<SYM>.parquet."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

RAW = Path(__file__).resolve().parents[3] / "data/raw/yahoo"
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{s}?period1=946684800&period2={p2}&interval=1d&events=div%7Csplit"
HDR = {"User-Agent": "Mozilla/5.0"}
UNIVERSE = {
    # FX spot (MT5 forex)
    "EURUSD=X": "EURUSD", "GBPUSD=X": "GBPUSD", "JPY=X": "USDJPY", "AUDUSD=X": "AUDUSD", "CAD=X": "USDCAD", "CHF=X": "USDCHF",
    "NZDUSD=X": "NZDUSD", "EURJPY=X": "EURJPY", "GBPJPY=X": "GBPJPY", "EURGBP=X": "EURGBP", "AUDJPY=X": "AUDJPY", "EURCHF=X": "EURCHF",
    # equity indices (MT5 index CFDs)
    "^GSPC": "US500", "^NDX": "US100", "^DJI": "US30", "^RUT": "US2000", "^GDAXI": "DE40", "^FTSE": "UK100", "^N225": "JP225",
    "^FCHI": "FR40", "^STOXX50E": "EU50", "^AXJO": "AU200", "^HSI": "HK50",
    # commodities / bonds via total-return ETFs (continuous, roll cost embedded) and futures for reference
    "GLD": "GOLD", "SLV": "SILVER", "USO": "WTI", "BNO": "BRENT", "UNG": "NATGAS", "CPER": "COPPER", "DBA": "AGRI",
    "TLT": "UST20Y", "IEF": "UST10Y",
    "GC=F": "GC_F", "CL=F": "CL_F", "ES=F": "ES_F", "NQ=F": "NQ_F", "ZN=F": "ZN_F", "^VIX": "VIX"}


def fetch(sym: str) -> pd.DataFrame:
    r = requests.get(URL.format(s=sym, p2=int(time.time())), headers=HDR, timeout=30).json()["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close", "volume")}, index=pd.to_datetime(r["timestamp"], unit="s"))
    df["adjclose"] = r["indicators"].get("adjclose", [{}])[0].get("adjclose", df["close"]) if r["indicators"].get("adjclose") else df["close"]
    df.index = df.index.normalize()
    df = df[~df.index.duplicated(keep="last")].dropna(subset=["close"])
    RAW.mkdir(parents=True, exist_ok=True); df.to_parquet(RAW / f"{UNIVERSE.get(sym, sym)}.parquet")
    return df


def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(RAW / f"{name}.parquet")


if __name__ == "__main__":
    for s in sys.argv[1:] or UNIVERSE:
        try:
            d = fetch(s); print(UNIVERSE.get(s, s), len(d), d.index.min().date(), d.index.max().date(), flush=True)
        except Exception as e:
            print(s, "FAILED", e, flush=True)
        time.sleep(1.0)

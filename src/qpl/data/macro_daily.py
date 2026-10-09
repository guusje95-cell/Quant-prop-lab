"""Daily close series through 2026 for MT5-tradable macro assets, from GitHub 'datasets' mirrors (FRED/EIA public data):
github.com/datasets/exchange-rates (FRED H.10, foreign currency per USD), datasets/oil-prices (EIA Brent/WTI spot),
datasets/natural-gas (EIA Henry Hub spot), datasets/s-and-p-500 archive/fred_sp500.csv (FRED SP500, 2016-02..2026-02).
Close-only (no intraday OHLC). Ingest: python -m qpl.data.macro_daily <dir with the cloned repos>"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROC = Path(__file__).resolve().parents[3] / "data/processed/macro"
FX = {"EURUSD": ("Euro", True), "GBPUSD": ("United Kingdom", True), "AUDUSD": ("Australia", True),
      "NZDUSD": ("New Zealand", True), "USDJPY": ("Japan", False), "USDCAD": ("Canada", False), "USDCHF": ("Switzerland", False)}


def ingest(root: Path) -> pd.DataFrame:
    fx = pd.read_csv(root / "exchange-rates/data/daily.csv", parse_dates=["Date"])
    cols = {}
    for pair, (country, invert) in FX.items():
        s = fx[fx.Country == country].set_index("Date")["Exchange rate"].astype(float)
        s = s[s > 0]
        cols[pair] = 1.0 / s if invert else s
    for name, f in (("WTI", "oil-prices/data/wti-daily.csv"), ("BRENT", "oil-prices/data/brent-daily.csv"), ("NATGAS", "natural-gas/data/daily.csv")):
        s = pd.read_csv(root / f, parse_dates=["Date"]).set_index("Date")["Price"].astype(float)
        cols[name] = s[s > 0]
    s = pd.read_csv(root / "s-and-p-500/archive/fred_sp500.csv", parse_dates=["observation_date"]).set_index("observation_date")["SP500"]
    cols["SPX"] = pd.to_numeric(s, errors="coerce").dropna()
    v = pd.read_csv(root / "finance-vix/data/vix-daily.csv", parse_dates=["DATE"]).set_index("DATE")["CLOSE"]
    cols["VIX"] = pd.to_numeric(v, errors="coerce").dropna()                  # datasets/finance-vix (CBOE), not tradable
    out = pd.DataFrame(cols).sort_index()
    out = out[~out.index.duplicated()]
    PROC.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROC / "macro_daily.parquet")
    return out


def load() -> pd.DataFrame:
    return pd.read_parquet(PROC / "macro_daily.parquet")


if __name__ == "__main__":
    d = ingest(Path(sys.argv[1]))
    print(d.apply(lambda s: (str(s.first_valid_index().date()), str(s.last_valid_index().date()), int(s.notna().sum()))).T)

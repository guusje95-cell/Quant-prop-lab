"""Crypto data loaders + validation (V4). All outputs UTC-indexed by bar OPEN time."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "ext"
PROC = ROOT / "data" / "processed" / "crypto"


def bitstamp_1m() -> pd.DataFrame:
    p = PROC / "bitstamp_btcusd_1m.parquet"
    if p.exists():
        return pd.read_parquet(p)
    base = RAW / "bitstamp-btcusd-minute-data" / "data"
    a = pd.read_csv(base / "historical" / "btcusd_bitstamp_1min_2012-2025.csv.gz")
    b = pd.read_csv(base / "updates" / "btcusd_bitstamp_1min_latest.csv")
    df = pd.concat([a, b], ignore_index=True)
    df["ts"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df.drop(columns="timestamp").set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="last")].astype(float)
    PROC.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p)
    return df


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """OHLCV resample (bar open labels, left-closed). Bars without any minute are dropped;
    `n_min` = minutes present, `n_traded` = minutes with volume > 0 (liquidity/quality proxy)."""
    g = df.resample(rule, label="left", closed="left")
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                        "close": g["close"].last(), "volume": g["volume"].sum(),
                        "n_min": g["close"].count(), "n_traded": g["volume"].apply(lambda v: int((v > 0).sum()))})
    return out.dropna(subset=["close"])


def btc_bars(rule: str = "1h") -> pd.DataFrame:
    p = PROC / f"bitstamp_btcusd_{rule}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    out = resample(bitstamp_1m(), rule)
    out.to_parquet(p)
    return out


def validate_1m(df: pd.DataFrame) -> dict:
    idx = df.index
    dt = np.diff(idx.asi8) / 60e6 if idx.dtype.unit == "us" else np.diff(idx.asi8) / 60e9
    gaps = dt[dt > 1]
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    yr = idx.year
    zero_vol = pd.Series(v == 0, index=idx).groupby(yr).mean()
    r = np.diff(np.log(c))
    rep = {"rows": int(len(df)), "start": str(idx[0]), "end": str(idx[-1]),
           "duplicates": int(idx.duplicated().sum()), "monotonic": bool(idx.is_monotonic_increasing),
           "ohlc_violations": int(((h < np.maximum(o, c)) | (l > np.minimum(o, c))).sum()),
           "nonpositive": int((c <= 0).sum()), "negative_volume": int((v < 0).sum()),
           "missing_minutes_total": int((gaps - 1).sum()), "gaps_over_60min": int((gaps > 60).sum()),
           "largest_gaps_min": sorted([float(x) for x in gaps])[-5:],
           "zero_volume_minute_share_by_year": {int(k): round(float(x), 3) for k, x in zero_vol.items()},
           "abs_1m_logret_gt_10pct": int((np.abs(r) > 0.10).sum())}
    return rep


def funding_binance_2020_2024(sym: str = "BTC") -> pd.Series:
    f = RAW / "historical-funding-rates-fetcher" / "data" / f"{sym}-USDT" / f"{sym}-USDT_binance_2020-01-01_2024-01-01_funding_history.csv"
    d = pd.read_csv(f)
    ts = pd.to_datetime(d["Date"]).dt.tz_localize("Etc/GMT-3").dt.tz_convert("UTC")   # file is UTC+3
    s = pd.Series(d["Funding Rate"].to_numpy(float), index=ts).sort_index()
    s = s[~s.index.duplicated()]
    assert set(s.index.hour) <= {0, 8, 16}, "funding timestamps not on Binance 00/08/16 UTC grid after shift"
    return s


def funding_recent(venue: str) -> pd.DataFrame:
    d = pd.read_parquet(RAW / "funding_rate_data" / "data" / "funding" / f"venue={venue}" / "data.parquet")
    d["settlement_ts"] = pd.to_datetime(d["settlement_ts"], utc=True)
    return d


def write_inventory() -> dict:
    df = bitstamp_1m()
    inv = {"bitstamp_btcusd_1m": validate_1m(df)}
    for s in ("BTC", "ETH"):
        f = funding_binance_2020_2024(s)
        inv[f"binance_funding_{s}"] = {"rows": len(f), "start": str(f.index[0]), "end": str(f.index[-1]),
                                       "mean_8h": float(f.mean()), "share_positive": float((f > 0).mean()),
                                       "max": float(f.max()), "min": float(f.min())}
    for v in ("binance", "bybit", "hyperliquid"):
        d = funding_recent(v)
        inv[f"funding_recent_{v}"] = {"rows": len(d), "symbols": int(d.venue_symbol.nunique()),
                                      "start": str(d.settlement_ts.min()), "end": str(d.settlement_ts.max()),
                                      "has_mark_price_share": float(d.mark_price.notna().mean())}
    (ROOT / "data" / "metadata").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "metadata" / "crypto_inventory.json").write_text(json.dumps(inv, indent=1, default=str))
    return inv

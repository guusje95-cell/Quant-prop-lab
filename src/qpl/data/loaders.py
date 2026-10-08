"""Raw -> processed loaders. All processed data is UTC-indexed parquet.

Bar timestamp convention (both sources): the timestamp is the bar OPEN time.
A bar stamped 14:30 with 15-minute frequency covers [14:30, 14:45).
Strategies may only use a bar's OHLC once the bar has closed, i.e. at
timestamp + bar_length. The backtester enforces this by executing signals
computed on bar t at the open of bar t+1.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
CFG = json.loads((ROOT / "config" / "data_sources.json").read_text())

COLS = ["open", "high", "low", "close", "volume"]


def _read_dukascopy_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    df.columns = [c.strip().lower() for c in df.columns]
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M:%S", utc=True)
    df = df.set_index("time").sort_index()
    df.index.name = "ts"
    return df[COLS].astype(float)


def _read_topstepx_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"].str.slice(0, 19), format="%Y-%m-%dT%H:%M:%S", utc=True)
    df = df.set_index("datetime").sort_index()
    df.index.name = "ts"
    return df[COLS].astype(float)


def raw_dukascopy(symbol: str, tf: str) -> pd.DataFrame:
    tpl = CFG["dukascopy_github"]["files"][symbol]
    return _read_dukascopy_csv(RAW / "dukascopy" / tpl.format(tf=tf))


def raw_topstepx(symbol: str, tf: str) -> pd.DataFrame:
    files = glob.glob(str(RAW / "topstepx" / symbol / f"{symbol}_{tf}_*.csv"))
    if not files:
        raise FileNotFoundError(f"{symbol} {tf}")
    return _read_topstepx_csv(Path(files[0]))


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Deterministic cleaning. Returns cleaned frame + log of every change."""
    log = {"rows_in": int(len(df))}
    dup = df.index.duplicated(keep="last")
    log["duplicates_dropped"] = int(dup.sum())
    df = df[~dup]
    nan = df[["open", "high", "low", "close"]].isna().any(axis=1)
    log["nan_rows_dropped"] = int(nan.sum())
    df = df[~nan]
    nonpos = (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    log["nonpositive_rows_dropped"] = int(nonpos.sum())
    df = df[~nonpos]
    # Repair (not drop) minor OHLC inconsistencies: high must be >= max(o,c), low <= min(o,c)
    hi_bad = df["high"] < df[["open", "close"]].max(axis=1)
    lo_bad = df["low"] > df[["open", "close"]].min(axis=1)
    log["high_repaired"] = int(hi_bad.sum())
    log["low_repaired"] = int(lo_bad.sum())
    df = df.copy()
    df.loc[hi_bad, "high"] = df.loc[hi_bad, ["open", "close"]].max(axis=1)
    df.loc[lo_bad, "low"] = df.loc[lo_bad, ["open", "close"]].min(axis=1)
    log["rows_out"] = int(len(df))
    return df, log


def processed_path(source: str, symbol: str, tf: str) -> Path:
    return PROC / source / f"{symbol}_{tf}.parquet"


def build_processed() -> dict:
    """Build all processed parquet files; return cleaning logs."""
    logs = {}
    for sym in CFG["dukascopy_github"]["files"]:
        for tf in CFG["dukascopy_github"]["timeframes"]:
            try:
                df, lg = clean(raw_dukascopy(sym, tf))
            except FileNotFoundError:
                continue
            p = processed_path("dukascopy", sym, tf)
            p.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(p)
            logs[f"dukascopy/{sym}_{tf}"] = lg
    for sym in CFG["topstepx_github"]["symbols"]:
        for tf in CFG["topstepx_github"]["timeframes"]:
            try:
                df, lg = clean(raw_topstepx(sym, tf))
            except FileNotFoundError:
                continue
            p = processed_path("topstepx", sym, tf)
            p.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(p)
            logs[f"topstepx/{sym}_{tf}"] = lg
    return logs


def load(source: str, symbol: str, tf: str) -> pd.DataFrame:
    p = processed_path(source, symbol, tf)
    if not p.exists():
        build_processed()
    return pd.read_parquet(p)

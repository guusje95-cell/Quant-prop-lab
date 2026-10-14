"""Backtest Lab data layer: every source returns a `Bars` object (wide OHLCV frames, one column per symbol).

Sources
  builtin:binance_daily   Binance spot daily candles, 10 majors (data/processed/crypto, from github.com/finom/static-klines)
  builtin:binance_hourly  same, hourly (2022+)
  local:okx_hourly        OKX USDT-perp hourly candles saved by qpl.data.okx (data/raw/okx)
  local:yahoo_daily       Yahoo daily candles saved by qpl.data.yahoo (data/raw/yahoo)
  lab:<file>              anything saved by `python -m qpl.lab.download ...` (data/lab/*.parquet, long format)
  csv upload              columns: time, [symbol], open, high, low, close, [volume]
All timestamps are tz-naive UTC. Bars are labelled by their OPEN time."""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "data/lab"
FIELDS = ("open", "high", "low", "close", "volume")
PPY = {"1h": 24 * 365, "4h": 6 * 365, "1d": 365, "1d_tradfi": 252}


@dataclass
class Bars:
    name: str
    freq: str                                  # '1h', '4h' or '1d'
    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame
    periods_per_year: float = 365.0
    extra: dict = field(default_factory=dict)  # e.g. {"stablecoin_cap": Series}

    @property
    def symbols(self):
        return list(self.close.columns)

    def select(self, symbols=None, start=None, end=None) -> "Bars":
        cols = symbols or self.symbols
        sl = slice(pd.Timestamp(start) if start else None, pd.Timestamp(end) if end else None)
        f = lambda d: d.loc[sl, [c for c in cols if c in d.columns]]
        b = Bars(self.name, self.freq, f(self.open), f(self.high), f(self.low), f(self.close), f(self.volume), self.periods_per_year, dict(self.extra))
        keep = b.close.notna().any(axis=1)
        for k in FIELDS:
            setattr(b, k, getattr(b, k).loc[keep])
        return b


def from_long(df: pd.DataFrame, name: str, freq: str) -> Bars:
    """long rows (time, symbol, open, high, low, close, volume) -> Bars."""
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_localize(None)
    if "symbol" not in df:
        df["symbol"] = "ASSET"
    if "volume" not in df:
        df["volume"] = np.nan
    df = df.drop_duplicates(["time", "symbol"], keep="last")
    w = {k: df.pivot(index="time", columns="symbol", values=k).sort_index().astype(float) for k in FIELDS}
    return Bars(name, freq, *(w[k] for k in FIELDS), periods_per_year=PPY.get(freq, 365.0))


def infer_freq(index: pd.DatetimeIndex) -> str:
    if len(index) < 3:
        return "1d"
    step = pd.Series(index).diff().median()
    if step <= pd.Timedelta("1h"):
        return "1h"
    if step <= pd.Timedelta("4h"):
        return "4h"
    return "1d"


def resample(b: Bars, freq: str) -> Bars:
    """Aggregate to a coarser timeframe ('4h' or '1d', UTC boundaries)."""
    if freq == b.freq:
        return b
    rule = {"4h": "4h", "1d": "1D"}[freq]
    o = b.open.resample(rule).first(); h = b.high.resample(rule).max(); lo = b.low.resample(rule).min()
    c = b.close.resample(rule).last(); v = b.volume.resample(rule).sum(min_count=1)
    keep = c.notna().any(axis=1)
    return Bars(b.name, freq, o[keep], h[keep], lo[keep], c[keep], v[keep], PPY[freq], dict(b.extra))


# ---------------------------------------------------------------- sources
def _binance_builtin(rule: str) -> Bars:
    from qpl.data import static_klines as SK
    d = SK.load(rule)
    freq = "1d" if rule == "1d" else "1h"
    return Bars(f"Binance spot majors {freq}", freq, *(d[k] for k in FIELDS), periods_per_year=PPY[freq])


def _okx_local() -> Bars:
    from qpl.data import okx as OK
    files = sorted(OK.RAW.glob("*-USDT-SWAP_1H.parquet"))
    if not files:
        raise FileNotFoundError("no OKX files: run `python -m qpl.lab.download okx --symbols BTC ETH ...`")
    D = {f.name.split("-")[0]: pd.read_parquet(f) for f in files}
    w = {k: pd.DataFrame({s: d[k] for s, d in D.items()}).sort_index() for k in ("open", "high", "low", "close")}
    w["volume"] = pd.DataFrame({s: d["volQuote"] for s, d in D.items()}).sort_index()
    return Bars("OKX USDT perps 1h", "1h", *(w[k] for k in FIELDS), periods_per_year=PPY["1h"])


def _yahoo_local() -> Bars:
    from qpl.data import yahoo as Y
    files = sorted(Y.RAW.glob("*.parquet"))
    if not files:
        raise FileNotFoundError("no Yahoo files: run `python -m qpl.lab.download yahoo --symbols ^GSPC GC=F ...`")
    D = {f.stem: pd.read_parquet(f) for f in files}
    w = {}
    for k in FIELDS:
        cols = {}
        for s, d in D.items():
            adj = (d["adjclose"] / d["close"]).where(d["close"] > 0) if "adjclose" in d else 1.0
            cols[s] = d[k] * (adj if k != "volume" else 1.0)
        w[k] = pd.DataFrame(cols).sort_index()
    return Bars("Yahoo daily", "1d", *(w[k] for k in FIELDS), periods_per_year=PPY["1d_tradfi"])


def _lab_file(path: Path) -> Bars:
    df = pd.read_parquet(path)
    freq = df.attrs.get("freq") or infer_freq(pd.DatetimeIndex(sorted(df["time"].unique())))
    return from_long(df, path.stem, freq)


def list_sources() -> dict:
    """name -> loader (only those whose files exist)."""
    out = {}
    p = ROOT / "data/processed/crypto"
    if (p / "binance_spot_majors_1d.parquet").exists():
        out["Binance spot majors (daily, 2017+)"] = lambda: _binance_builtin("1d")
    if (p / "binance_spot_majors_1h.parquet").exists():
        out["Binance spot majors (hourly, 2022+)"] = lambda: _binance_builtin("1h")
    if list((ROOT / "data/raw/okx").glob("*_1H.parquet")):
        out["OKX USDT perps (hourly, 2020+)"] = _okx_local
    if list((ROOT / "data/raw/yahoo").glob("*.parquet")):
        out["Yahoo daily (indices, FX, ETFs, futures)"] = _yahoo_local
    if LAB.exists():
        for f in sorted(LAB.glob("*.parquet")):
            out[f"Downloaded: {f.stem}"] = (lambda f=f: _lab_file(f))
    return out


def read_csv(buf, name="uploaded CSV") -> Bars:
    df = pd.read_csv(io.BytesIO(buf) if isinstance(buf, (bytes, bytearray)) else buf)
    df.columns = [c.strip().lower() for c in df.columns]
    for alias in ("date", "datetime", "timestamp", "ts"):
        if "time" not in df and alias in df:
            df = df.rename(columns={alias: "time"})
    need = {"time", "open", "high", "low", "close"}
    if not need <= set(df.columns):
        raise ValueError(f"CSV needs columns {sorted(need)} (+ optional symbol, volume); got {list(df.columns)}")
    if pd.api.types.is_numeric_dtype(df["time"]):
        unit = "ms" if df["time"].max() > 1e11 else "s"
        df["time"] = pd.to_datetime(df["time"], unit=unit)
    freq = infer_freq(pd.DatetimeIndex(sorted(pd.to_datetime(df["time"]).unique())))
    return from_long(df, name, freq)


def stablecoin_caps() -> pd.Series | None:
    """USDT+USDC market cap per day (Coin Metrics files if present, else data/lab/stablecoins.parquet)."""
    try:
        from qpl.data import coinmetrics as CM
        cap = lambda a: pd.read_csv(CM.SRC / f"{a}.csv", usecols=["time", "CapMrktCurUSD"], parse_dates=["time"]).set_index("time")["CapMrktCurUSD"]
        s = cap("usdt").fillna(0).add(cap("usdc"), fill_value=0)
        s.index = s.index.tz_localize(None) if s.index.tz is not None else s.index
        lab = LAB / "stablecoins.parquet"
        if lab.exists():
            t = pd.read_parquet(lab)["cap"]
            s = pd.concat([s, t[t.index > s.index.max()]])
        return s
    except Exception:
        lab = LAB / "stablecoins.parquet"
        return pd.read_parquet(lab)["cap"] if lab.exists() else None

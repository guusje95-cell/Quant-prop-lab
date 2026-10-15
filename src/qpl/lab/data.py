"""Backtest Lab data layer: every source returns a `Bars` object (wide OHLCV frames, one column per symbol).

Sources
  builtin:binance_daily   Binance spot daily candles, 10 majors (data/processed/crypto, from github.com/finom/static-klines)
  builtin:binance_hourly  same, hourly (2022+)
  local:okx_hourly        OKX USDT-perp hourly candles saved by qpl.data.okx (data/raw/okx)
  local:yahoo_daily       Yahoo daily candles saved by qpl.data.yahoo (data/raw/yahoo)
  local:dukascopy         US100 / US500 CFD 5-min, 15-min, hourly from the research data (data/raw/dukascopy)
  local:futures_panel     ~250 futures, daily total-return index (data/processed/futures_panel)
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
FREQS = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]                     # supported bar lengths, finest first
BPD = {"1m": 1440, "5m": 288, "15m": 96, "30m": 48, "1h": 24, "4h": 6, "1d": 1}   # bars per 24h day
RULE = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D"}


def periods_per_year(index: pd.DatetimeIndex, freq: str) -> float:
    """Bars per year as observed in the data (a futures market trading 23h x 5 days has fewer bars than crypto's 24/7)."""
    if len(index) > 50:
        span = (index[-1] - index[0]).days / 365.25
        if span >= 0.04:
            return float(len(index) / span)
    return float(BPD.get(freq, 1) * 365)


@dataclass
class Bars:
    name: str
    freq: str                                  # one of FREQS: '1m', '5m', '15m', '30m', '1h', '4h', '1d'
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
    return Bars(name, freq, *(w[k] for k in FIELDS), periods_per_year=periods_per_year(w["close"].index, freq))


def infer_freq(index: pd.DatetimeIndex) -> str:
    if len(index) < 3:
        return "1d"
    step = pd.Series(index).diff().median()
    for f in FREQS[:-1]:
        if step <= pd.Timedelta(RULE.get(f, "1min")):
            return f
    return "1d"


def resample(b: Bars, freq: str) -> Bars:
    """Aggregate to a coarser timeframe (one of FREQS, UTC boundaries)."""
    if freq == b.freq:
        return b
    rule = RULE[freq]
    o = b.open.resample(rule).first(); h = b.high.resample(rule).max(); lo = b.low.resample(rule).min()
    c = b.close.resample(rule).last(); v = b.volume.resample(rule).sum(min_count=1)
    keep = c.notna().any(axis=1)
    return Bars(b.name, freq, o[keep], h[keep], lo[keep], c[keep], v[keep], periods_per_year(c[keep].index, freq), dict(b.extra))


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


def _dukascopy_github(sym: str, tf: str) -> Bars:
    from qpl.data import loaders as L
    df = L.raw_dukascopy(sym, tf)
    df.index = df.index.tz_localize(None)
    freq = {"M5": "5m", "M15": "15m", "M30": "30m", "H1": "1h", "D1": "1d"}[tf]
    w = {k: df[[k]].rename(columns={k: sym}) for k in FIELDS}
    return Bars(f"Dukascopy {sym} {freq}", freq, *(w[k] for k in FIELDS), periods_per_year=periods_per_year(df.index, freq))


def _dukascopy_all(tf: str = "H1") -> Bars:
    """All 13 Dukascopy CFDs in the research data (4 indices, gold, silver, Brent, 6 FX), one Bars."""
    from qpl.data import loaders as L
    fr = {}
    for sym in L.CFG["dukascopy_github"]["files"]:
        try:
            x = L.raw_dukascopy(sym, tf); x.index = x.index.tz_localize(None); fr[sym] = x
        except Exception:
            pass
    w = {k: pd.DataFrame({s: d[k] for s, d in fr.items()}).sort_index() for k in FIELDS}
    freq = {"M15": "15m", "H1": "1h"}[tf]
    return Bars(f"Dukascopy {len(fr)} CFDs {freq}", freq, *(w[k] for k in FIELDS), periods_per_year=periods_per_year(w["close"].index, freq))


def futures_tr_index(ret: pd.DataFrame) -> pd.DataFrame:
    """Daily futures returns (back-adjusted P&L / contract price) -> total-return index starting at 100 (roll gaps removed)."""
    return 100 * (1 + ret.fillna(0)).cumprod().where(ret.notna().cumsum() > 0)


def _futures_panel() -> Bars:
    r = pd.read_parquet(ROOT / "data/processed/futures_panel/ret.parquet")
    r.index = pd.DatetimeIndex(r.index).tz_localize(None) if getattr(r.index, "tz", None) else pd.DatetimeIndex(r.index)
    c = futures_tr_index(r)
    nan = c * np.nan
    return Bars("Futures daily (pysystemtrade)", "1d", c, c, c, c, nan, periods_per_year=PPY["1d_tradfi"])


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
    for sym in ("US100", "US500"):
        for tf, lab in (("M5", "5-min, 2020-23"), ("M15", "15-min"), ("H1", "hourly")):
            try:
                from qpl.data import loaders as L
                if (L.RAW / "dukascopy" / L.CFG["dukascopy_github"]["files"][sym].format(tf=tf)).exists():
                    out[f"{sym} CFD, Dukascopy ({lab})"] = (lambda sym=sym, tf=tf: _dukascopy_github(sym, tf))
            except Exception:
                pass
    try:
        from qpl.data import loaders as L
        if (L.RAW / "dukascopy" / L.CFG["dukascopy_github"]["files"]["EURUSD"].format(tf="H1")).exists():
            out["Dukascopy 13 CFDs: indices, gold, silver, Brent, FX (hourly, 2013-23)"] = lambda: _dukascopy_all("H1")
    except Exception:
        pass
    from qpl.lab import futures_curve as FC
    if FC.CACHE.exists() or FC.LOCAL.exists():
        out["Commodity futures curve, 3 contracts (daily, to 2024-03)"] = FC.bars
        out["Futures daily, 250 markets (pysystemtrade, to 2024-03)"] = _futures_panel
    if LAB.exists():
        for f in sorted(LAB.glob("*.parquet")):
            if f.stem in ("stablecoins", "futures_curve"):
                continue
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
    """USDT+USDC market cap per day, cut at QPL_CUTOFF (paper trading) when set: a day's value counts as known at the end of the day."""
    import os
    s = _stablecoin_caps_all()
    if s is not None and os.environ.get("QPL_CUTOFF"):
        s = s[s.index + pd.Timedelta(days=1) <= pd.Timestamp(os.environ["QPL_CUTOFF"])]
    return s


def _stablecoin_caps_all() -> pd.Series | None:
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

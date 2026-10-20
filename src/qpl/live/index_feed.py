"""Live hourly BID bars for the bf index sleeve (US100/US500/US30, Dukascopy public datafeed, no account, no key), in the
research_data/dukascopy/<SYM>_1h.parquet format, written to <live>/dukascopy/. Run on your own PC (Dukascopy throttles the
research cloud).

    python -m qpl.live.index_feed paper_trading/bf2/data

Finished months come from the monthly hour-candle files (as in the research download); the current month is built from the
hourly tick files (BID side), which Dukascopy publishes shortly after each hour, so the 13:00 and 15:00 ET signal bars are
available the same day. The first run after a gap can take several minutes (one request per hour per index, paced)."""
import lzma
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from qpl.lab import download as DL

ROOT = Path(__file__).resolve().parents[3]
SYMBOLS = ("US100", "US500", "US30")
URL = "https://datafeed.dukascopy.com/datafeed/{inst}/{y}/{m:02d}/{d:02d}/{h:02d}h_ticks.bi5"


def _scale(raw_median, symbol):
    lo, hi = DL.DUKA_RANGE[symbol]
    for k in range(8):
        if lo <= raw_median / 10 ** k <= hi:
            return 10 ** k
    raise RuntimeError(f"{symbol}: price scale not found (median raw {raw_median})")


def tick_hour(symbol, hour: pd.Timestamp):
    """One UTC hour of BID ticks -> (open, high, low, close, volume) or None (no ticks) or 'FAILED: ...'."""
    url = URL.format(inst=DL.DUKA_SYM[symbol], y=hour.year, m=hour.month - 1, d=hour.day, h=hour.hour)
    reason = ""
    for k in range(4):
        try:
            r = DL._duka_get(url)
            if r.status_code == 404 or (r.status_code == 200 and not r.content):
                DL._pace(True); return None
            if r.status_code == 200:
                raw = lzma.decompress(r.content); DL._pace(True)
                a = np.frombuffer(raw[: len(raw) // 20 * 20], dtype=np.dtype([("t", ">u4"), ("ask", ">i4"), ("bid", ">i4"), ("av", ">f4"), ("bv", ">f4")]))
                if len(a) == 0:
                    return None
                b = a["bid"].astype(float); s = _scale(float(np.median(b)), symbol); b = b / s
                return (b[0], b.max(), b.min(), b[-1], float(a["bv"].sum()))
            reason = f"HTTP {r.status_code}"
        except Exception as e:                                 # network error / bad file: cool down and retry
            reason = type(e).__name__; DL._DUKA = None
        DL._pace(False)
    return f"FAILED: {reason}"


def update(data_dir: Path, now: pd.Timestamp | None = None, log=print) -> bool:
    out = Path(data_dir) / "dukascopy"; out.mkdir(parents=True, exist_ok=True); ok = True
    now = (pd.Timestamp.now("UTC").tz_localize(None) if now is None else pd.Timestamp(now)).floor("h")
    for s in SYMBOLS:
        try:
            ok &= _update_one(s, out, now, log)
        except Exception as e:                                 # never stop the paper run: the cutoff waits at most 1 hour
            log(f"  {s}: not updated ({e.__class__.__name__}: {e})"); ok = False
    return ok


def _update_one(s, out, now, log) -> bool:
    ok = True
    if True:
        f = out / f"{s}_1h.parquet"; base = ROOT / f"research_data/dukascopy/{s}_1h.parquet"
        old = pd.read_parquet(f) if f.exists() else None
        last = max(pd.read_parquet(p).index.max() for p in (f, base) if p.exists())
        parts = [old] if old is not None else []
        month0 = now.replace(day=1).normalize()
        if last < month0 - pd.Timedelta(hours=1):              # finished months: monthly hour-candle files
            try:
                x = DL.duka_hourly(s, start=str(last.normalize()), end=str(month0 - pd.Timedelta(days=1)))
                x = x.set_index("time")[["open", "high", "low", "close", "volume"]]; parts.append(x); last = max(last, x.index.max())
            except Exception as e:
                log(f"  {s}: month candles not available ({e})"); ok = False
        rows = {}                                              # the current month (no monthly file yet): hourly tick files
        for h in pd.date_range(max(month0, last - pd.Timedelta(hours=3)), now - pd.Timedelta(hours=1), freq="h"):
            if h.dayofweek == 5 or (h.dayofweek == 4 and h.hour >= 22) or (h.dayofweek == 6 and h.hour < 21):
                continue                                       # index CFDs are closed (no tick files to fetch)
            v = tick_hour(s, h)
            if isinstance(v, str):
                log(f"  {s} {h}: {v}"); ok = False; break             # stop at the first failed hour: no gaps
            if v is not None and v[4] > 0:
                rows[h] = v
        if rows:
            parts.append(pd.DataFrame.from_dict(rows, orient="index", columns=["open", "high", "low", "close", "volume"]))
        if parts:
            d = pd.concat(parts); d.index = pd.DatetimeIndex(d.index).astype("datetime64[us]"); d.index.name = "time"
            d = d[~d.index.duplicated(keep="last")].sort_index().astype("float32"); d.to_parquet(f)
            log(f"  {s}: last bar {d.index.max()}")
    return ok


if __name__ == "__main__":
    update(Path(sys.argv[1]) if sys.argv[1:] else ROOT / "paper_trading/bf2/data")

"""bf index sleeve 'vol-managed indices' (Gen234 = P6 vol-managed long + R1 dip ensemble at 14:00 ET + P1 IBS at 16:00 ET) on
US100/US500/US30 CFDs, for paper trading: Dukascopy hourly BID bars from the research copy + QPL_LIVE_PACK/dukascopy overlay, a bar
counting once its hour is over (QPL_CUTOFF). Reproduces gen147 p6() + r1(1e-4) + gen232 p1() exactly on the research data.

    python scripts/index_sleeve.py check

legs(idx) -> {leg: (positions DataFrame by symbol, hourly P&L)}; sleeve(idx) -> (positions summed by symbol, P&L)."""
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
DUK = ROOT / "research_data/dukascopy"
COST = 1e-4


def hourly(s):
    frames = [pd.read_parquet(DUK / f"{s}_1h.parquet")]
    live = os.environ.get("QPL_LIVE_PACK")
    if live and (Path(live) / "dukascopy" / f"{s}_1h.parquet").exists():
        frames.append(pd.read_parquet(Path(live) / "dukascopy" / f"{s}_1h.parquet"))
    x = pd.concat(frames).astype("float64"); x.index = pd.DatetimeIndex(x.index)
    x = x[~x.index.duplicated(keep="last")].sort_index(); x = x[x.close > 0]
    cut = os.environ.get("QPL_CUTOFF")
    return x[x.index + pd.Timedelta(hours=1) <= pd.Timestamp(cut)] if cut else x


def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _event_leg(x, idx, hour_et, signal):
    """Signal at the close of the hour_et ET bar (RTH from 09:00 ET), position from the next bar, held until the next signal."""
    et = x.index.tz_localize("UTC").tz_convert("America/New_York"); d = pd.Series(pd.DatetimeIndex(et.date), index=x.index)
    wk = et.weekday < 5; snap = wk & (et.hour == hour_et); rth = wk & (et.hour >= 9) & (et.hour <= hour_et)
    c = x.close[snap].groupby(d[snap]).last(); hi = x.high[rth].groupby(d[rth]).max().reindex(c.index); lo = x.low[rth].groupby(d[rth]).min().reindex(c.index)
    sig = signal(c, hi, lo)
    start = pd.Series(sig.to_numpy(), index=x.index[snap][~d[snap].duplicated(keep="last").to_numpy()] + pd.Timedelta(hours=1))
    return start.reindex(idx.union(start.index)).ffill().reindex(idx).fillna(0.0)


def r1_signal(c, hi, lo):
    ibs = (c - lo) / (hi - lo)
    ind = [(rsi2(c) < 10), (c <= c.rolling(5).min()), (c.diff().lt(0).rolling(3).sum() == 3), (ibs < 0.3)]
    return 0.25 * (sum(z.astype(float) for z in ind) / 4).where(hi > lo, 0.0)


def p1_signal(c, hi, lo):
    return 0.25 * (((c - lo) / (hi - lo)) < 0.3).astype(float).where(hi > lo, 0.0)


def legs(idx):
    out = {"P6": {}, "R1": {}, "P1": {}}
    for s in ("US100", "US500", "US30"):
        x = hourly(s); r = x.close.reindex(idx).ffill(limit=72).pct_change().fillna(0.0)
        if s != "US30":
            dret = r.groupby(r.index.floor("D")).sum(); vol = dret.rolling(20).std() * np.sqrt(252)
            out["P6"][s] = ((0.5 * (0.15 / vol).clip(upper=2.0)).shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0), r)
            out["P1"][s] = (_event_leg(x, idx, 15, p1_signal), r)
        out["R1"][s] = (_event_leg(x, idx, 13, r1_signal), r)
    res = {}
    for leg, d in out.items():
        pos = pd.DataFrame({s: w for s, (w, _) in d.items()})
        pnl = sum(w * r - w.diff().abs().fillna(0.0) * COST for w, r in d.values())
        res[leg] = (pos, pnl)
    return res


def sleeve(idx):
    L = legs(idx)
    pos = sum(p.reindex(columns=["US100", "US500", "US30"]).fillna(0.0) for p, _ in L.values())
    return pos, sum(h for _, h in L.values())


if __name__ == "__main__" and sys.argv[1:] == ["check"]:
    os.environ.pop("QPL_LIVE_PACK", None); os.environ.pop("QPL_CUTOFF", None)
    g = {"__file__": str(ROOT / "scripts/gen232_bf_p1.py")}; exec(open(ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], g)
    IDXbf = g["IDXbf"]; ref = g["p6"]() + g["r1"](1e-4) + g["p1"]()
    _, mine = sleeve(IDXbf)
    print("hours", len(ref), "max abs diff", float((mine - ref).abs().max()))

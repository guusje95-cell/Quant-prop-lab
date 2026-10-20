"""Gen124 (config/gen124_protocol.json): intraday news-minute continuation (08:30 / 14:00 ET) and RTH gap fade.
Primary: Databento 1-minute ES/NQ futures; replication: Dukascopy 5-minute US500/US100 CFDs. Bars are labelled by their START.
Writes results/gen124.csv and results/gen124_daily.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
SPL = (("2018-01-01", "2020-12-31"), ("2021-01-01", "2023-12-31"), ("2024-01-01", "2026-09-30"))


def sharpe(p, a, b):
    x = p.loc[a:b]; x = x[x.index.weekday < 5]
    return float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else float("nan")


def bars_futures(root):
    d = pd.read_parquet(F.DB / f"{root}_1m.parquet")
    d = d[d.symbol.astype(str).str.endswith(".v.0")]
    d.index = pd.to_datetime(d["ts_event"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    d = d[~d.index.duplicated()].sort_index().loc[:"2026-09-30 23:59"]
    return d[["open", "high", "low", "close", "instrument_id"]].astype({"open": float, "high": float, "low": float, "close": float})


def bars_cfd(sym):
    d = pd.read_parquet(ROOT / f"research_data/dukascopy/{sym}_5m.parquet").astype(float)
    d.index = d.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    d["instrument_id"] = 0
    return d[~d.index.duplicated()].sort_index().loc[:"2026-09-30 23:59"]


def at(day_bars, hhmm, field):
    t = day_bars.index[day_bars.index.strftime("%H:%M") == hhmm]
    return (day_bars.loc[t[0], field], day_bars.loc[t[0], "instrument_id"]) if len(t) else (np.nan, None)


def last_before(day_bars, hhmm, field="close"):
    x = day_bars[day_bars.index.strftime("%H:%M") < hhmm]
    return (x[field].iloc[-1], x["instrument_id"].iloc[-1]) if len(x) else (np.nan, None)


def news(bars, t0, t1, t_exit, cost):
    """t0..t1 detection window (bar-start times), enter at the price at t1 (last close before t1), exit at the price at t_exit."""
    out, hist = {}, []
    for day, g in bars.groupby(bars.index.normalize()):
        if day.weekday() >= 5:
            continue
        p0, i0 = at(g, t0, "open"); p1, i1 = last_before(g, t1); px, ix = last_before(g, t_exit)
        if not (np.isfinite(p0) and np.isfinite(p1) and np.isfinite(px)) or len({i0, i1, ix}) > 1:
            continue
        m = p1 / p0 - 1; med = np.median(hist[-60:]) if len(hist) >= 40 else np.nan; hist.append(abs(m))
        if np.isfinite(med) and abs(m) > 4 * med:
            side = np.sign(m); out[day] = side * (px / p1 - 1) - 2 * cost(p1)
    return pd.Series(out, dtype=float)


def gap_fade(bars, cost, tick_frac):
    out, prev_close, prev_id = {}, np.nan, None
    for day, g in bars.groupby(bars.index.normalize()):
        if day.weekday() >= 5:
            continue
        o, io = at(g, "09:30", "open")
        if np.isfinite(o) and np.isfinite(prev_close) and io == prev_id:
            gap = o / prev_close - 1
            if abs(gap) > 0.004:
                side = -np.sign(gap); tgt = prev_close; stop = o * (1 + np.sign(gap) * abs(gap))
                w = g[(g.index.strftime("%H:%M") >= "09:30") & (g.index.strftime("%H:%M") < "11:00")]
                res = None
                for _, b in w.iterrows():
                    hit_stop = (b.high >= stop) if side < 0 else (b.low <= stop)
                    hit_tgt = (b.low <= tgt) if side < 0 else (b.high >= tgt)
                    if hit_stop:
                        res = side * (stop / o - 1) - tick_frac(o); break
                    if hit_tgt:
                        res = side * (tgt / o - 1); break
                if res is None and len(w):
                    res = side * (w.close.iloc[-1] / o - 1)
                if res is not None:
                    out[day] = res - 2 * cost(o)
        c, ic = last_before(g, "16:00")
        prev_close, prev_id = c, ic
    return pd.Series(out, dtype=float)


rows, PNL = [], {}


def report(name, per_market):
    p = pd.concat(per_market, axis=1).fillna(0.0).mean(axis=1)            # 0.5 each when both markets trade
    days = pd.date_range("2018-01-01", "2026-09-30", freq="B"); p = p.reindex(days).fillna(0.0)
    k = tuple(round(sharpe(p, a, b), 3) for a, b in SPL)
    r = {"test": name, "DEV": k[0], "TEST": k[1], "HOLD": k[2], "pass": bool(k[0] > 0 and k[1] >= 0.5 and k[2] >= 0.3),
         "trades": int(sum((s != 0).sum() for s in per_market)), "mean per trade bp": round(float(pd.concat(per_market).mean() * 1e4), 2)}
    rows.append(r); PNL[name] = p; print(r, flush=True); return r


def run(tag, B, cost, tick):
    report(f"J1 08:30 continuation [{tag}]", [news(B[m], "08:30", "08:35", "10:00", cost[m]) for m in B])
    report(f"J2 14:00 continuation [{tag}]", [news(B[m], "14:00", "14:05", "15:55", cost[m]) for m in B])
    report(f"J3 RTH gap fade [{tag}]", [gap_fade(B[m], cost[m], tick[m]) for m in B])


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("cfd", "both"):
        B = {s: bars_cfd(s) for s in ("US500", "US100")}
        run("CFD 5m", B, {s: (lambda p: 1e-4) for s in B}, {s: (lambda p: 1e-4) for s in B})
    if which in ("futures", "both"):
        B = {r: bars_futures(r) for r in ("ES", "NQ")}
        run("futures 1m", B, {r: (lambda p, r=r: F.cost_frac(r, p)) for r in B}, {r: (lambda p, r=r: F.SPEC[r][0] / p) for r in B})
    pd.DataFrame(rows).to_csv(ROOT / f"results/gen124_{which}.csv", index=False)
    pd.DataFrame(PNL).to_parquet(ROOT / f"results/gen124_{which}_daily.parquet")

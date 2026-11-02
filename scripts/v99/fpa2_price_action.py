"""FPA-2 (research/v99/fpa2_protocol.json). Writes results/v99/fpa2_price_action.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/v99"))
import fpa1_price_action as F


def load_local(s, tz):
    x = pd.read_parquet(ROOT / f"research_data/dukascopy/{s}_5m.parquet")[["open", "high", "low", "close"]].astype(float)
    x = x[x.close > 0]; x.index = x.index.tz_localize("UTC").tz_convert(tz).tz_localize(None)
    return x[~x.index.duplicated()].sort_index()


def sessions(x, a, z):
    out = []
    for d in sorted(set(x.index.normalize())):
        if d.weekday() >= 5:
            continue
        R = x.loc[d:d + pd.Timedelta(hours=23, minutes=59)].between_time(a, z)
        if len(R) >= 60:
            out.append((d, R))
    return out


def breakout(R, start, end_scan, hi, lo, stop_fn, exit_t):
    for t, b in R.between_time(start, end_scan).iterrows():
        if b.close > hi or b.close < lo:
            side = 1 if b.close > hi else -1
            return F.trade(R.loc[t + pd.Timedelta(minutes=5):exit_t] if isinstance(exit_t, pd.Timestamp) else R.loc[t + pd.Timedelta(minutes=5):], side, b.close, stop_fn(side))
    return None


def run_us(x):
    S = sessions(x, "09:30", "15:55"); out = {"Q1": {}, "Q2": {}, "Q3": {}}; hist = []; prev_close = None
    for i, (d, R) in enumerate(S):
        hi_, lo_ = R.high.max(), R.low.min(); atr = np.mean([h[2] for h in hist[-14:]]) if len(hist) >= 14 else None
        if len(hist) >= 2 and atr:
            (_, h1, _, l1), (_, h2, _, l2) = (hist[-1][0], hist[-1][1], 0, hist[-1][3]), (hist[-2][0], hist[-2][1], 0, hist[-2][3])
            OR = R.between_time("09:30", "09:55"); oh, ol = OR.high.max(), OR.low.min()
            if h1 < h2 and l1 > l2:                                                  # Q1 inside day
                r = breakout(R, "10:00", "15:50", oh, ol, lambda s: ol if s > 0 else oh, None)
                if r is not None: out["Q1"][d] = r
            IB = R.between_time("09:30", "10:25"); ih, il = IB.high.max(), IB.low.min()
            if (ih - il) / IB.close.iloc[-1] < 0.5 * atr:                           # Q2 narrow initial balance
                mid = (ih + il) / 2; r = breakout(R, "10:30", "15:50", ih, il, lambda s: mid, None)
                if r is not None: out["Q2"][d] = r
            o = R.open.iloc[0]; g = o / prev_close - 1
            if abs(g) / atr > 0.6:                                                   # Q3 confirmed gap-and-go
                F30 = R.between_time("09:30", "09:55"); side = np.sign(g)
                filled = (prev_close - F30.low.min()) / (prev_close - o) if side > 0 else (F30.high.max() - prev_close) / (o - prev_close)
                worst = (o - F30.low.min()) / (o - prev_close) if side > 0 else (F30.high.max() - o) / (prev_close - o)
                c10 = F30.close.iloc[-1]
                if (c10 - o) * side > 0 and worst < 0.5:
                    stop = F30.low.min() if side > 0 else F30.high.max()
                    r = F.trade(R.between_time("10:00", "15:55"), side, c10, stop)
                    if r is not None: out["Q3"][d] = r
        hist.append((d, hi_, (max(hi_, prev_close or hi_) - min(lo_, prev_close or lo_)) / R.close.iloc[-1], lo_))
        prev_close = R.close.iloc[-1]
    return {k: pd.Series(v, dtype=float) for k, v in out.items()}


def run_de(x):
    S = sessions(x, "09:00", "17:25"); out = {}; ranges = []
    for d, R in S:
        if len(ranges) >= 6 and ranges[-1] <= min(ranges[-7:]):
            OR = R.between_time("09:00", "09:25"); oh, ol = OR.high.max(), OR.low.min()
            r = breakout(R, "09:30", "17:20", oh, ol, lambda s: ol if s > 0 else oh, None)
            if r is not None: out[d] = r
        ranges.append((R.high.max() - R.low.min()) / R.close.iloc[-1])
    return pd.Series(out, dtype=float)


def main():
    bd = pd.bdate_range("2018-01-01", "2026-10-16"); res = {m: run_us(F.load(m)) for m in F.MKTS}; out = {}
    for k in ("Q1", "Q2", "Q3"):
        daily = sum(res[m][k].reindex(bd).fillna(0.0) for m in F.MKTS) / len(F.MKTS); T = pd.concat([res[m][k] for m in F.MKTS])
        dev, jud = F.sharpe(daily, "2018", "2022"), F.sharpe(daily, "2023", "2026")
        out[k] = {"trades": int(len(T)), "win rate": round(float((T > 0).mean()), 3) if len(T) else None, "Sharpe dev / judge": [dev, jud],
                  "per market judge": {m: F.sharpe(res[m][k].reindex(bd).fillna(0.0), "2023", "2026") for m in F.MKTS},
                  "pass": bool(dev is not None and jud is not None and dev >= 0.5 and jud >= 0.5)}
        print(k, out[k], flush=True)
    de = run_de(load_local("DE40", "Europe/Berlin")).reindex(bd).fillna(0.0)
    dev, jud = F.sharpe(de, "2018", "2022"), F.sharpe(de, "2023", "2026")
    out["Q4 DE40 replication of P5"] = {"trades": int((de != 0).sum()), "Sharpe dev / judge": [dev, jud], "pass": bool(dev is not None and jud is not None and dev >= 0.5 and jud >= 0.5)}
    print(out["Q4 DE40 replication of P5"], flush=True)
    (ROOT / "results/v99/fpa2_price_action.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

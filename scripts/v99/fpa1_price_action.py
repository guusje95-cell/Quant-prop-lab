"""FPA-1 (research/v99/fpa1_protocol.json): five intraday price-action families on US500 / US100 / US30 5-minute bars (ES / NQ / YM
proxies). Writes results/v99/fpa1_price_action.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
MKTS = ["US500", "US100", "US30"]; COST = 1e-4; RISK = 0.0025; LEV = 4.0


def load(s):
    x = pd.read_parquet(ROOT / f"research_data/dukascopy/{s}_5m.parquet")[["open", "high", "low", "close"]].astype(float)
    x = x[x.close > 0]; t = x.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    x.index = t; return x[~x.index.duplicated()].sort_index()


def trade(bars, side, entry, stop, target=None):
    """walk 5-minute bars after the entry bar; returns the net return on equity (risk-sized)"""
    dist = abs(entry - stop) / entry
    if dist <= 0:
        return None
    size = min(RISK / dist, LEV); px = bars.close.iloc[-1] if len(bars) else entry
    for _, b in bars.iterrows():
        if (side > 0 and b.low <= stop) or (side < 0 and b.high >= stop):
            px = stop; break
        if target is not None and ((side > 0 and b.high >= target) or (side < 0 and b.low <= target)):
            px = target; break
    return size * (side * (px / entry - 1) - 2 * COST)


def run(x):
    days = sorted(set(x.index.normalize())); out = {k: {} for k in ("P1", "P2", "P3", "P4", "P5")}
    rth = {}; prev_close = None; ranges = []; atrs = []
    for d in days:
        D = x.loc[d:d + pd.Timedelta(hours=23, minutes=59)]
        R = D.between_time("09:30", "15:55")
        if len(R) < 60 or d.weekday() >= 5:
            continue
        rth[d] = R
        rng = (R.high.max() - R.low.min()) / R.close.iloc[-1]
        ON = x.loc[d - pd.Timedelta(hours=6):d + pd.Timedelta(hours=9, minutes=25)]       # 18:00 previous day .. 09:25
        atr = np.mean(atrs[-14:]) if len(atrs) >= 14 else None
        if prev_close is not None and atr:
            o = R.open.iloc[0]; g = o / prev_close - 1; c935 = R.close.iloc[0]
            # P1 gap fill
            if 0.1 <= abs(g) / atr <= 0.6:
                side = -np.sign(g); r = trade(R.between_time("09:35", "11:55"), side, c935, c935 * (1 - side * abs(g)), prev_close)
                if r is not None: out["P1"][d] = r
            # P2 gap and go
            f15 = R.between_time("09:30", "09:40")
            if abs(g) / atr > 0.6 and len(f15) == 3 and np.sign(f15.close.iloc[-1] - o) == np.sign(g):
                side = np.sign(g); stop = f15.low.min() if side > 0 else f15.high.max()
                r = trade(R.between_time("09:45", "15:55"), side, f15.close.iloc[-1], stop)
                if r is not None: out["P2"][d] = r
            # P3 overnight sweep-reclaim
            if len(ON) > 50:
                oh, ol = ON.high.max(), ON.low.min(); mid = (oh + ol) / 2
                for t, b in R.between_time("09:30", "10:25").iterrows():
                    if b.high > oh and b.close < oh:
                        r = trade(R.loc[t + pd.Timedelta(minutes=5):], -1, b.close, b.high, mid)
                        if r is not None: out["P3"][d] = r
                        break
                    if b.low < ol and b.close > ol:
                        r = trade(R.loc[t + pd.Timedelta(minutes=5):], 1, b.close, b.low, mid)
                        if r is not None: out["P3"][d] = r
                        break
            # P4 VWAP pullback on trend days (volume-free VWAP proxy: typical-price running mean; Dukascopy volume is tick volume)
            H1 = R.between_time("09:30", "10:25")
            mv = H1.close.iloc[-1] / o - 1
            if abs(mv) > 0.4 * atr:
                dside = np.sign(mv); midH = (H1.high.max() + H1.low.min()) / 2
                if (H1.close.iloc[-1] - midH) * dside > 0:
                    tp = (R.high + R.low + R.close) / 3; vw = tp.expanding().mean()
                    for t, b in R.between_time("10:30", "13:55").iterrows():
                        if (dside > 0 and b.low <= vw.loc[t]) or (dside < 0 and b.high >= vw.loc[t]):
                            stop = H1.low.min() if dside > 0 else H1.high.max()
                            if (b.close - stop) * dside > 0:
                                r = trade(R.loc[t + pd.Timedelta(minutes=5):], dside, b.close, stop)
                                if r is not None: out["P4"][d] = r
                            break
            # P5 NR7 + 30-minute opening range
            if len(ranges) >= 6 and ranges[-1] <= min(ranges[-7:]):
                OR = R.between_time("09:30", "09:55"); hi, lo = OR.high.max(), OR.low.min()
                for t, b in R.between_time("10:00", "15:50").iterrows():
                    if b.close > hi or b.close < lo:
                        side = 1 if b.close > hi else -1
                        r = trade(R.loc[t + pd.Timedelta(minutes=5):], side, b.close, lo if side > 0 else hi)
                        if r is not None: out["P5"][d] = r
                        break
        tr = (max(R.high.max(), prev_close or R.high.max()) - min(R.low.min(), prev_close or R.low.min())) / R.close.iloc[-1]
        atrs.append(tr); ranges.append(rng); prev_close = R.close.iloc[-1]
    return {k: pd.Series(v, dtype=float) for k, v in out.items()}


def sharpe(s, a, z):
    s = s.loc[a:z]; return round(float(s.mean() / s.std() * np.sqrt(252)), 3) if len(s) > 20 and s.std() > 0 else None


def main():
    res = {m: run(load(m)) for m in MKTS}
    bd = pd.bdate_range("2018-01-01", "2026-10-16"); out = {}
    for k in ("P1", "P2", "P3", "P4", "P5"):
        daily = sum(res[m][k].reindex(bd).fillna(0.0) for m in MKTS) / len(MKTS)
        dev, jud = sharpe(daily, "2018", "2022"), sharpe(daily, "2023", "2026")
        T = pd.concat([res[m][k] for m in MKTS])
        out[k] = {"trades": int(len(T)), "win rate": round(float((T > 0).mean()), 3) if len(T) else None,
                  "mean R (per 0.25% risk)": round(float(T.mean() / RISK), 3) if len(T) else None,
                  "Sharpe dev 2018-22": dev, "Sharpe judge 2023-26": jud,
                  "per market judge": {m: sharpe(res[m][k].reindex(bd).fillna(0.0), "2023", "2026") for m in MKTS},
                  "pass": bool(dev is not None and jud is not None and dev >= 0.5 and jud >= 0.5)}
        print(k, out[k], flush=True)
    (ROOT / "results/v99/fpa1_price_action.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

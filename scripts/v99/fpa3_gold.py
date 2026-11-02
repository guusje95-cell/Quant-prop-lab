"""FPA-3 (research/v99/fpa3_protocol.json): gold session / event families on XAUUSD 5-minute bars. Writes results/v99/fpa3_gold.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/v99"))
import fpa1_price_action as F
COST = 1e-4


def load(tz):
    x = pd.read_parquet(ROOT / "research_data/dukascopy/XAUUSD_5m.parquet")[["open", "high", "low", "close"]].astype(float)
    x = x[x.close > 0]; x.index = x.index.tz_localize("UTC").tz_convert(tz).tz_localize(None)
    return x[~x.index.duplicated()].sort_index()


def px_at(c, t):
    """close of the last 5-minute bar starting before t (bar labelled by its start, so its close is known at start + 5 min)"""
    s = c.loc[:t - pd.Timedelta(minutes=5)]
    return s.iloc[-1] if len(s) and (t - s.index[-1]) <= pd.Timedelta(hours=3) else np.nan


def main():
    ny = load("America/New_York"); ld = load("Europe/London"); c, cl = ny.close, ld.close
    days = pd.bdate_range("2018-01-03", "2026-10-16"); out = {}
    G1, G2, G4, BH = {}, {}, {}, {}
    rng = []
    for d in days:
        a, b, e = px_at(c, d - pd.Timedelta(hours=6)), px_at(c, d + pd.Timedelta(hours=8, minutes=20)), px_at(c, d + pd.Timedelta(hours=17))
        if np.isfinite([a, b, e]).all():
            G1[d] = (b / a - 1) - (e / b - 1) - 4 * COST; BH[d] = e / a - 1
        p1, p2, p3, p4 = (px_at(cl, d + pd.Timedelta(hours=h, minutes=m)) for h, m in ((9, 30), (10, 30), (10, 40), (12, 0)))
        if np.isfinite([p1, p2, p3, p4]).all() and abs(p2 / p1 - 1) >= 5e-4:
            G2[d] = -np.sign(p2 / p1 - 1) * (p4 / p3 - 1) - 2 * COST
        D = ny.loc[d:d + pd.Timedelta(hours=23, minutes=59)]
        if len(D):
            rng.append((D.high.max() - D.low.min()) / D.close.iloc[-1])
        q1, q2, q3 = (px_at(c, d + pd.Timedelta(hours=h, minutes=m)) for h, m in ((8, 30), (8, 45), (11, 30)))
        if len(rng) > 14 and np.isfinite([q1, q2, q3]).all() and abs(q2 / q1 - 1) > 0.3 * np.mean(rng[-15:-1]):
            G4[d] = np.sign(q2 / q1 - 1) * (q3 / q2 - 1) - 2 * COST
    # G3: P5 on the COMEX session
    G3 = {}; ranges = []
    for d in days:
        R = ny.loc[d:d + pd.Timedelta(hours=23, minutes=59)].between_time("08:20", "13:25")
        if len(R) < 50:
            continue
        if len(ranges) >= 6 and ranges[-1] <= min(ranges[-7:]):
            OR = R.between_time("08:20", "08:45"); hi, lo = OR.high.max(), OR.low.min()
            for t, bb in R.between_time("08:50", "13:20").iterrows():
                if bb.close > hi or bb.close < lo:
                    side = 1 if bb.close > hi else -1; F.COST = COST
                    r = F.trade(R.loc[t + pd.Timedelta(minutes=5):], side, bb.close, lo if side > 0 else hi)
                    if r is not None: G3[d] = r
                    break
        ranges.append((R.high.max() - R.low.min()) / R.close.iloc[-1])
    bh = pd.Series(BH).reindex(days).fillna(0.0)
    for k, v in (("G1 overnight minus day", G1), ("G2 London AM fix fade", G2), ("G3 P5 replication on gold", G3), ("G4 US 08:30 data drift", G4)):
        s = pd.Series(v, dtype=float).reindex(days).fillna(0.0)
        dev, jud = F.sharpe(s, "2018", "2022"), F.sharpe(s, "2023", "2026")
        out[k] = {"active days": int((s != 0).sum()), "Sharpe dev / judge": [dev, jud], "corr with gold": round(float(s.corr(bh)), 3),
                  "pass": bool(dev is not None and jud is not None and dev >= 0.5 and jud >= 0.5)}
        print(k, out[k], flush=True)
    out["reference: gold buy-and-hold (18:00 -> 17:00 ET daily)"] = [F.sharpe(bh, "2018", "2022"), F.sharpe(bh, "2023", "2026")]
    print(out["reference: gold buy-and-hold (18:00 -> 17:00 ET daily)"])
    (ROOT / "results/v99/fpa3_gold.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

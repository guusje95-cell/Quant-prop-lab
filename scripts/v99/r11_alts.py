"""v9.9 R11 (research/v99/r11_protocol.json): the least-bad R9/R10 price-action rules on 15 altcoin perps, plus a trend-filtered week
breakout on all 20 coins. Writes results/v99/r11_alts.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B
import r8_levels as R8
import r9_sessions as R9
import r10_liquidity as R10
MAJ = ["BTC", "ETH", "SOL", "BNB", "XRP"]
ALTS = ["AAVE", "ADA", "ATOM", "AVAX", "BCH", "DOGE", "DOT", "ETC", "FIL", "LINK", "LTC", "NEAR", "TRX", "UNI", "XLM"]
RISK, CAP = 0.0025, 5.0


def set_cost(c):
    R8.COST = R9.TAKER = R10.TAKER = c


def week_break_trend(k1, cost):
    """R8 'break' rules on weekly levels with 1-hour bars; long only above / short only below the 50-day average of daily closes."""
    k = k1.loc["2021-12-01":"2026-09-30 23:55"]; key = k.index.to_period("W-SUN").start_time
    dc = k1.close.groupby(k1.index.floor("D")).last()                # full history, so the 50-day average exists from Jan 2022
    trend = (dc > dc.rolling(50).mean()).astype(float) - (dc < dc.rolling(50).mean()).astype(float)
    trend = trend.shift(1)                                           # previous completed day
    g = k.groupby(key); lv = pd.DataFrame({"H": g.high.max().shift(1), "L": g.low.min().shift(1)}); out = []
    for p, x in g:
        if np.isnan(lv.loc[p, "H"]):
            continue
        h, l, c, t = x.high.to_numpy(), x.low.to_numpy(), x.close.to_numpy(), x.index
        tr = trend.reindex(t.floor("D")).to_numpy()
        for side, level in ((1, lv.loc[p, "H"]), (-1, lv.loc[p, "L"])):
            for i in range(len(c)):
                if (side > 0 and c[i] > level) or (side < 0 and c[i] < level):
                    if tr[i] != side:
                        break                                        # first break is against the trend: no trade this week/side
                    entry, stop = c[i], (l[i] if side > 0 else h[i]); dist = abs(entry - stop) / entry
                    if dist <= 0:
                        break
                    tgt = entry + side * 2 * abs(entry - stop); size = min(RISK / dist, CAP)
                    for j in range(i + 1, len(c)):
                        hs = l[j] <= stop if side > 0 else h[j] >= stop; ht = h[j] >= tgt if side > 0 else l[j] <= tgt
                        if hs or ht:
                            px = stop if hs else tgt; break
                    else:
                        j, px = len(c) - 1, c[-1]
                    out.append((t[j], size * (side * (px / entry - 1) - 2 * cost)))
                    break
    return out


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    b0 = unit(CS.portfolio_v5(V8)[0]); ref = [shp(b0, "2022", "2026-09-30"), per(b0)]
    K5 = {c: B.k5(c)[["open", "high", "low", "close"]].loc["2021-10-01":"2026-09-30 23:55"] for c in MAJ + ALTS}
    K1 = {c: k.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna() for c, k in K5.items()}
    def two(T):                                                      # R10 returns (time, net, gross)
        return [(x[0], x[1]) for x in T]
    TESTS = {"A week breakout on 1-hour closes (alts)": (ALTS, lambda c: (set_cost(8e-4), R8.trades(K1[c], "W", "break"))[1]),
             "B equal highs/lows breakout (alts)": (ALTS, lambda c: (set_cost(8e-4), two(R10.pool_trades(K1[c], "break")))[1]),
             "C Asia-range breakout (alts)": (ALTS, lambda c: (set_cost(8e-4), R9.session_trades(K5[c], "A"))[1]),
             "D week breakout with 50-day trend filter (20 coins)": (MAJ + ALTS, lambda c: week_break_trend(K1[c], 6e-4 if c in MAJ else 8e-4))}
    out = {"reference v9.8": ref}
    for name, (coins, fn) in TESTS.items():
        T = [x for c in coins for x in fn(c) if x[0] >= pd.Timestamp("2022-01-01")]
        s = pd.Series([v for _, v in T], index=pd.DatetimeIndex([x for x, _ in T])).groupby(level=0).sum()
        hp = s.groupby(s.index.floor("h")).sum().reindex(idx).fillna(0.0) / len(coins); R = np.array([v for _, v in T]) / RISK
        b = unit(CS.portfolio_v5(V8.assign(**{name: hp}))[0]); r = [shp(b, "2022", "2026-09-30"), per(b)]
        out[name] = {"trades": len(T), "win rate": round(float((R > 0).mean()), 3), "mean R after costs": round(float(R.mean()), 3),
                     "sleeve 2022 / 23-24 / 25-26": per(hp), "book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    (ROOT / "results/v99/r11_alts.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

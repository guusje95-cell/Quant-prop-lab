"""v9.9 R10 (research/v99/r10_protocol.json): round-number and equal-highs/lows (liquidity pool) trades on 1-hour bars with 1:2 RR and a
minimum stop of 1 ATR. Writes results/v99/r10_liquidity.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B
COINS = ["BTC", "ETH", "SOL", "BNB", "XRP"]; RISK, TAKER, CAP, HOLD = 0.0025, 6e-4, 5.0, 48


def walk(h, l, c, t, i, side, entry, stop):
    """from bar i+1 up to i+HOLD: stop first; returns (exit index, exit time, net, gross) as fractions of the sleeve"""
    dist = abs(entry - stop) / entry; tgt = entry + side * 2 * abs(entry - stop); size = min(RISK / dist, CAP); last = min(i + HOLD, len(c) - 1)
    for j in range(i + 1, last + 1):
        hs = l[j] <= stop if side > 0 else h[j] >= stop; ht = h[j] >= tgt if side > 0 else l[j] <= tgt
        if hs or ht:
            px = stop if hs else tgt; break
    else:
        j, px = last, c[last]
    g = size * side * (px / entry - 1); return j, t[j], g - size * 2 * TAKER, g


def atr(k):
    tr = pd.concat([k.high - k.low, (k.high - k.close.shift()).abs(), (k.low - k.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(24).mean().to_numpy()


def stop_for(side, entry, extreme, a):
    return max(extreme * 1.0002, entry + a) if side < 0 else min(extreme * 0.9998, entry - a)


def round_trades(k):
    t = k.index; o, h, l, c = (k[x].to_numpy() for x in ("open", "high", "low", "close")); A = atr(k); out = []; busy = -1
    for i in range(24, len(c) - 1):
        if i <= busy or np.isnan(A[i]):
            continue
        step = 10 ** np.floor(np.log10(o[i])) / 2
        up, dn = np.ceil(o[i] / step) * step, np.floor(o[i] / step) * step
        side = -1 if (h[i] > up > c[i]) else 1 if (l[i] < dn < c[i]) else 0
        if side:
            r = walk(h, l, c, t, i, side, c[i], stop_for(side, c[i], h[i] if side < 0 else l[i], A[i])); out.append(r[1:]); busy = r[0]
    return out


def pools(h, l, n=3, lookback=120, tol=0.0015):
    """yield (confirm bar, kind 'H'/'L', level): two pivots within `lookback` bars, prices within tol, never exceeded in between"""
    ev = []
    for kind, x in (("H", h), ("L", l)):
        piv = [p for p in range(n, len(x) - n) if (x[p] == x[p - n:p + n + 1].max() if kind == "H" else x[p] == x[p - n:p + n + 1].min())]
        for a, p2 in enumerate(piv):
            for p1 in reversed(piv[:a]):
                if p2 - p1 > lookback:
                    break
                lv = max(x[p1], x[p2]) if kind == "H" else min(x[p1], x[p2])
                if abs(x[p1] / x[p2] - 1) <= tol:
                    mid = x[p1 + 1:p2]
                    if len(mid) and ((kind == "H" and mid.max() > lv) or (kind == "L" and mid.min() < lv)):
                        continue
                    ev.append((p2 + n, kind, lv)); break
    return sorted(ev)


def pool_trades(k, mode):
    t = k.index; h, l, c = (k[x].to_numpy() for x in ("high", "low", "close")); A = atr(k); out = []; busy = -1
    active = []; ev = pools(h, l); e = 0
    for i in range(24, len(c) - 1):
        while e < len(ev) and ev[e][0] <= i:
            active.append([ev[e][0], ev[e][1], ev[e][2]]); e += 1
        active = [p for p in active if i - p[0] <= 120]
        for p in list(active):
            _, kind, lv = p
            broke = h[i] > lv if kind == "H" else l[i] < lv
            if not broke:
                continue
            active.remove(p)                                             # a pool is used once
            if i <= busy or np.isnan(A[i]):
                continue
            if mode == "sweep":
                back = c[i] < lv if kind == "H" else c[i] > lv
                if not back:
                    continue
                side = -1 if kind == "H" else 1; st = stop_for(side, c[i], h[i] if side < 0 else l[i], A[i])
            else:
                beyond = c[i] > lv if kind == "H" else c[i] < lv
                if not beyond:
                    continue
                side = 1 if kind == "H" else -1; st = c[i] - side * A[i]
            r = walk(h, l, c, t, i, side, c[i], st); out.append(r[1:]); busy = r[0]
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
    K1 = {c: B.k5(c)[["open", "high", "low", "close"]].loc["2021-12-01":"2026-09-30 23:55"].resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna() for c in COINS}
    TESTS = {"A round-number sweep-reclaim": round_trades, "B equal highs/lows sweep-reclaim": lambda k: pool_trades(k, "sweep"),
             "C equal highs/lows breakout": lambda k: pool_trades(k, "break")}
    out = {"reference v9.8": ref}
    for name, fn in TESTS.items():
        T = [x for c in COINS for x in fn(K1[c]) if x[0] >= pd.Timestamp("2022-01-01")]
        s = pd.Series([v for _, v, _ in T], index=pd.DatetimeIndex([x for x, _, _ in T])).groupby(level=0).sum()
        hp = s.groupby(s.index.floor("h")).sum().reindex(idx).fillna(0.0) / len(COINS)
        R, G = np.array([v for _, v, _ in T]) / RISK, np.array([g for _, _, g in T]) / RISK
        b = unit(CS.portfolio_v5(V8.assign(**{name: hp}))[0]); r = [shp(b, "2022", "2026-09-30"), per(b)]
        out[name] = {"trades": len(T), "win rate": round(float((R > 0).mean()), 3), "mean R gross": round(float(G.mean()), 3),
                     "mean R after costs": round(float(R.mean()), 3), "sleeve 2022 / 23-24 / 25-26": per(hp), "book": r,
                     "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    (ROOT / "results/v99/r10_liquidity.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

"""v9.9 R9 (research/v99/r9_protocol.json): session ranges, FVG fills and hourly level trades with 1:2 RR. Writes results/v99/r9_sessions.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B
COINS = ["BTC", "ETH", "SOL", "BNB", "XRP"]; RISK, TAKER, MAKER, CAP = 0.0025, 6e-4, 2e-4, 5.0


def run_trade(h, l, c, t, i0, side, entry, stop, last, entry_cost):
    """walk bars i0+1..last for stop / target (stop first if both); returns (exit_time, pnl fraction of the sleeve) or None"""
    dist = abs(entry - stop) / entry
    if dist <= 1e-5:
        return None
    tgt = entry + side * 2 * abs(entry - stop); size = min(RISK / dist, CAP)
    for i in range(i0 + 1, last + 1):
        hs = l[i] <= stop if side > 0 else h[i] >= stop; ht = h[i] >= tgt if side > 0 else l[i] <= tgt
        if hs or ht:
            px = stop if hs else tgt; return t[i], size * (side * (px / entry - 1) - entry_cost - TAKER)
    return t[last], size * (side * (c[last] / entry - 1) - entry_cost - TAKER)


def session_trades(k, mode):
    out = []
    for d, x in k.groupby(k.index.floor("D")):
        t = x.index; h, l, c = x.high.to_numpy(), x.low.to_numpy(), x.close.to_numpy(); hr = t.hour + t.minute / 60
        if mode in ("A", "B"):
            rng = (hr < 8); win = (hr >= 8) & (hr < 16)
        else:
            rng = (hr >= 13.5) & (hr < 14); win = (hr >= 14) & (hr < 20)
        if rng.sum() < 3 or win.sum() == 0:
            continue
        H, L = h[rng].max(), l[rng].min(); mid = (H + L) / 2; last = len(c) - 1
        idx = np.where(win)[0]
        if mode in ("A", "C"):
            for i in idx:
                if c[i] > H or c[i] < L:
                    side = 1 if c[i] > H else -1; stop = mid if mode == "A" else (L if side > 0 else H)
                    r = run_trade(h, l, c, t, i, side, c[i], stop, last, TAKER); out += [r] if r else []; break
        else:
            for side, lvl in ((-1, H), (1, L)):
                ext = None
                for i in idx:
                    if side < 0 and h[i] > lvl: ext = max(ext or h[i], h[i])
                    if side > 0 and l[i] < lvl: ext = min(ext or l[i], l[i])
                    if ext is not None and ((side < 0 and c[i] < lvl) or (side > 0 and c[i] > lvl)):
                        r = run_trade(h, l, c, t, i, side, c[i], ext * (1.0002 if side < 0 else 0.9998), last, TAKER); out += [r] if r else []; break
    return out


def fvg_trades(k1):
    t = k1.index; h, l, c = k1.high.to_numpy(), k1.low.to_numpy(), k1.close.to_numpy(); out = []; busy = -1
    for i in range(2, len(c) - 1):
        if i <= busy:
            continue
        for side in (1, -1):
            if side > 0 and l[i] > h[i - 2]: lim, stop = l[i], h[i - 2] * 0.9998
            elif side < 0 and h[i] < l[i - 2]: lim, stop = h[i], l[i - 2] * 1.0002
            else: continue
            for j in range(i + 1, min(i + 25, len(c))):
                if (side > 0 and l[j] <= lim) or (side < 0 and h[j] >= lim):
                    if (side > 0 and l[j] <= stop) or (side < 0 and h[j] >= stop):   # stop also hit in the fill bar -> loss
                        size = min(RISK / (abs(lim - stop) / lim), CAP); r = (t[j], size * (side * (stop / lim - 1) - MAKER - TAKER))
                    else:
                        r = run_trade(h, l, c, t, j, side, lim, stop, min(j + 48, len(c) - 1), MAKER)
                    if r:
                        out.append(r); busy = t.get_loc(r[0])
                    break
            break
    return out


def hourly_level_trades(k1, period, mode):
    import r8_levels as R8                                     # same rules as R8, 1-hour bars (r8 runs only under __main__)
    return R8.trades(k1, period, mode)


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    b0 = unit(CS.portfolio_v5(V8)[0]); ref = [shp(b0, "2022", "2026-09-30"), per(b0)]
    K5 = {c: B.k5(c)[["open", "high", "low", "close"]].loc["2021-12-01":"2026-09-30 23:55"] for c in COINS}
    K1 = {c: k.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna() for c, k in K5.items()}
    TESTS = {"A Asia-range breakout": lambda c: session_trades(K5[c], "A"), "B Asia-range sweep (Judas)": lambda c: session_trades(K5[c], "B"),
             "C NY opening-range breakout": lambda c: session_trades(K5[c], "C"), "D 1-hour FVG fill (limit)": lambda c: fvg_trades(K1[c]),
             "E day sweep on 1-hour closes": lambda c: hourly_level_trades(K1[c], "D", "sweep"), "F week breakout on 1-hour closes (FLAGGED)": lambda c: hourly_level_trades(K1[c], "W", "break")}
    out = {"reference v9.8": ref}
    for name, fn in TESTS.items():
        T = [x for c in COINS for x in fn(c)]
        s = pd.Series([v for _, v in T], index=pd.DatetimeIndex([x for x, _ in T])).groupby(level=0).sum()
        hp = s.groupby(s.index.floor("h")).sum().reindex(idx).fillna(0.0) / len(COINS); R = np.array([v for _, v in T]) / RISK
        b = unit(CS.portfolio_v5(V8.assign(**{name: hp}))[0]); r = [shp(b, "2022", "2026-09-30"), per(b)]
        out[name] = {"trades": len(T), "win rate": round(float((R > 0).mean()), 3), "mean R after costs": round(float(R.mean()), 3),
                     "sleeve 2022 / 23-24 / 25-26": per(hp), "book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    (ROOT / "results/v99/r9_sessions.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

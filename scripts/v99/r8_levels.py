"""v9.9 R8 (research/v99/r8_protocol.json): PDH/PDL and PWH/PWL sweep-reclaim and breakout trades with a fixed 1:2 risk-reward on
5-minute Binance perps. Writes results/v99/r8_levels.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B
COINS = ["BTC", "ETH", "SOL", "BNB", "XRP"]; RISK, COST, CAP = 0.0025, 6e-4, 5.0


def trades(k, period, mode):
    """k: 5-min OHLC. period 'D' or 'W'. mode 'sweep' or 'break'. Returns list of (exit_time, pnl_fraction_of_sleeve)."""
    k = k.loc["2021-12-01":"2026-09-30 23:55"]; key = k.index.floor("D") if period == "D" else k.index.to_period("W-SUN").start_time
    g = k.groupby(key); hi, lo = g.high.max(), g.low.min(); lv = pd.DataFrame({"H": hi.shift(1), "L": lo.shift(1)})
    out = []
    for p, x in g:
        if p not in lv.index or np.isnan(lv.loc[p, "H"]):
            continue
        H, L = lv.loc[p, "H"], lv.loc[p, "L"]; o, h, l, c = x.open.to_numpy(), x.high.to_numpy(), x.low.to_numpy(), x.close.to_numpy(); t = x.index
        for side, level in ((-1, H), (1, L)) if mode == "sweep" else ((1, H), (-1, L)):
            entry = stop = None; ext = None
            for i in range(len(c)):
                if entry is None:
                    if mode == "sweep":
                        if side < 0:
                            if h[i] > level:
                                ext = h[i] if ext is None else max(ext, h[i])
                            if ext is not None and c[i] < level:
                                entry, stop = c[i], ext * 1.0002
                        else:
                            if l[i] < level:
                                ext = l[i] if ext is None else min(ext, l[i])
                            if ext is not None and c[i] > level:
                                entry, stop = c[i], ext * 0.9998
                    else:
                        if (side > 0 and c[i] > level) or (side < 0 and c[i] < level):
                            entry, stop = c[i], (l[i] if side > 0 else h[i])
                    if entry is not None:
                        dist = abs(entry - stop) / entry
                        if dist <= 0:
                            entry = None; break
                        tgt = entry + side * 2 * abs(entry - stop); size = min(RISK / dist, CAP); j0 = i
                    continue
                hit_stop = (l[i] <= stop) if side > 0 else (h[i] >= stop); hit_tgt = (h[i] >= tgt) if side > 0 else (l[i] <= tgt)
                if hit_stop or hit_tgt:
                    px = stop if hit_stop else tgt; out.append((t[i], size * (side * (px / entry - 1) - 2 * COST))); break
            else:
                if entry is not None:
                    out.append((t[-1], size * (side * (c[-1] / entry - 1) - 2 * COST)))
    return out


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda h: h.groupby(h.index.floor("D")).sum()
    unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(h, a, z):
        d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", "2026-09-30")]
    b0 = unit(CS.portfolio_v5(V8)[0]); ref = [shp(b0, "2022", "2026-09-30"), per(b0)]
    K = {c: B.k5(c)[["open", "high", "low", "close"]] for c in COINS}
    out = {"reference v9.8": ref}
    for name, per_, mode in (("S1 day sweep-reclaim", "D", "sweep"), ("S2 day breakout", "D", "break"), ("S3 week sweep-reclaim", "W", "sweep"), ("S4 week breakout", "W", "break")):
        T = [x for c in COINS for x in trades(K[c], per_, mode)]
        s = pd.Series([v for _, v in T], index=pd.DatetimeIndex([t for t, _ in T])).groupby(level=0).sum()
        h = s.groupby(s.index.floor("h")).sum().reindex(idx).fillna(0.0) / len(COINS)
        R = np.array([v for _, v in T]) / RISK
        b = unit(CS.portfolio_v5(V8.assign(**{name: h}))[0]); r = [shp(b, "2022", "2026-09-30"), per(b)]
        out[name] = {"trades": len(T), "trades per coin per year": round(len(T) / len(COINS) / 4.75, 1), "win rate (R > 0)": round(float((R > 0).mean()), 3),
                     "mean R per trade after costs": round(float(R.mean()), 3), "sleeve 2022 / 23-24 / 25-26": per(h), "book": r,
                     "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    (ROOT / "results/v99/r8_levels.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

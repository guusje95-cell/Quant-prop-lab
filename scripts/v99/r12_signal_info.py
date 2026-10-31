"""v9.9 R12 (research/v99/r12_protocol.json): directional information of the R8-R11 price-action entry signals (forward returns after
the signal, no stop / target). Writes results/v99/r12_signal_info.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
from qpl.lab import binance_pack as B
import r10_liquidity as R10
HZ = (1, 4, 24)


def level_signals(k, period, mode):
    key = k.index.floor("D") if period == "D" else k.index.to_period("W-SUN").start_time
    g = k.groupby(key); lv = pd.DataFrame({"H": g.high.max().shift(1), "L": g.low.min().shift(1)}); pos = {t: i for i, t in enumerate(k.index)}; ev = []
    for p, x in g:
        if np.isnan(lv.loc[p, "H"]):
            continue
        H, L = lv.loc[p, "H"], lv.loc[p, "L"]; h, l, c = x.high.to_numpy(), x.low.to_numpy(), x.close.to_numpy()
        for side, lvl in ((1, H), (-1, L)):                                      # side = direction of the break
            for i in range(len(c)):
                if mode == "break" and ((side > 0 and c[i] > lvl) or (side < 0 and c[i] < lvl)):
                    ev.append((pos[x.index[i]], side)); break
                if mode == "sweep" and ((side > 0 and h[i] > lvl and c[i] < lvl) or (side < 0 and l[i] < lvl and c[i] > lvl)):
                    ev.append((pos[x.index[i]], -side)); break
    return ev


def asia_signals(k, mode):
    pos = {t: i for i, t in enumerate(k.index)}; ev = []
    for d, x in k.groupby(k.index.floor("D")):
        hr = x.index.hour; rng = x[hr < 8]; win = x[(hr >= 8) & (hr < 16)]
        if len(rng) < 6 or win.empty:
            continue
        H, L = rng.high.max(), rng.low.min()
        if mode == "break":
            for t, r in win.iterrows():
                if r.close > H or r.close < L:
                    ev.append((pos[t], 1 if r.close > H else -1)); break
        else:
            for side, lvl in ((1, H), (-1, L)):
                for t, r in win.iterrows():
                    if (side > 0 and r.high > lvl and r.close < lvl) or (side < 0 and r.low < lvl and r.close > lvl):
                        ev.append((pos[t], -side)); break
    return ev


def pool_signals(k):
    h, l, c = k.high.to_numpy(), k.low.to_numpy(), k.close.to_numpy(); ev = []; active = []; P = R10.pools(h, l); e = 0
    for i in range(len(c)):
        while e < len(P) and P[e][0] <= i:
            active.append(P[e]); e += 1
        active = [p for p in active if i - p[0] <= 120]
        for p in list(active):
            _, kind, lv = p
            if (kind == "H" and h[i] > lv) or (kind == "L" and l[i] < lv):
                active.remove(p)
                if (kind == "H" and c[i] > lv) or (kind == "L" and c[i] < lv):
                    ev.append((i, 1 if kind == "H" else -1))
    return ev


def round_signals(k):
    o, h, l, c = (k[x].to_numpy() for x in ("open", "high", "low", "close")); ev = []
    for i in range(len(c)):
        step = 10 ** np.floor(np.log10(o[i])) / 2; up, dn = np.ceil(o[i] / step) * step, np.floor(o[i] / step) * step
        if h[i] > up > c[i]:
            ev.append((i, -1))
        elif l[i] < dn < c[i]:
            ev.append((i, 1))
    return ev


def stats(df):
    out = {}
    for hz in HZ:
        x = df[f"r{hz}"].dropna()
        day = x.groupby(df.loc[x.index, "day"]).sum(); n = len(x)
        se = np.sqrt((day ** 2).sum()) / n if n else np.nan                       # day-clustered standard error of the mean
        out[f"{hz}h"] = {"n": n, "mean bp": round(float(x.mean() * 1e4), 2), "t": round(float(x.mean() / se), 2) if se > 0 else None}
    return out


def main():
    SIG = {"S1 day-level break": lambda k: level_signals(k, "D", "break"), "S2 day-level sweep-reclaim": lambda k: level_signals(k, "D", "sweep"),
           "S3 week-level break": lambda k: level_signals(k, "W", "break"), "S4 week-level sweep-reclaim": lambda k: level_signals(k, "W", "sweep"),
           "S5 Asia-range break": lambda k: asia_signals(k, "break"), "S6 Asia-range sweep-reclaim": lambda k: asia_signals(k, "sweep"),
           "S7 equal highs/lows break": pool_signals, "S8 round-number sweep-reclaim": round_signals}
    K1 = {c: B.k5(c)[["open", "high", "low", "close"]].loc["2021-12-01":"2026-09-30 23:55"].resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna() for c in B.coins()}
    out = {}
    for name, fn in SIG.items():
        rows = []
        for coin, k in K1.items():
            c = k.close.to_numpy(); t = k.index
            for i, side in fn(k):
                if t[i] < pd.Timestamp("2022-01-01"):
                    continue
                r = {"day": t[i].floor("D"), "late": t[i] >= pd.Timestamp("2025-01-01")}
                for hz in HZ:
                    r[f"r{hz}"] = side * (c[i + hz] / c[i] - 1) if i + hz < len(c) else np.nan
                rows.append(r)
        D = pd.DataFrame(rows)
        a, b = stats(D[~D.late]), stats(D[D.late])
        cand = [hz for hz in a if a[hz]["t"] is not None and b[hz]["t"] is not None and abs(a[hz]["mean bp"]) > 16 and abs(b[hz]["mean bp"]) > 16
                and abs(a[hz]["t"]) >= 3 and abs(b[hz]["t"]) >= 3 and np.sign(a[hz]["mean bp"]) == np.sign(b[hz]["mean bp"])]
        out[name] = {"2022-24": a, "2025-26": b, "passes gate at": cand}
        print(name, json.dumps(out[name]), flush=True)
    (ROOT / "results/v99/r12_signal_info.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

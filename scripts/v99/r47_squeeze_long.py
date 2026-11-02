"""v9.9 R47 (research/v99/r47_protocol.json): long after event-short stop-outs (squeeze continuation). Writes results/v99/r47_squeeze_long.json."""
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
import r16_coinbase as R16
import r22_upbit_r16rules as R22
import r23_meta_event as R23
import r30b_checks as RB
import r32_binance_tag_sleeves as R32
import r34_binance_add as R34
import r42_hodler as R42
RISK = 1.5


def stops(idx):
    s8, T = R23.trades(idx); out = []
    for t in T:
        hold = 14 if t["col"].startswith("spo_") else 30
        d = (t["exit"] - t["entry"]).total_seconds() / 86400
        if d < hold - 1.5 and t["exit"] < idx[-1] - pd.Timedelta(days=2):
            out.append((t["col"][4:] if t["col"].startswith("spo_") else t["col"], t["exit"]))
    return s8, out


def long_sleeve(ev, idx):
    pnl = pd.Series(0.0, index=idx); used = []; busy = {}
    P = pd.DataFrame(0.0, index=idx, columns=sorted({c for c, _ in ev}))
    for c, t in sorted(ev, key=lambda e: e[1]):
        if c in busy and t < busy[c]:
            continue
        cl, fu = EL._closes(c)
        if cl is None:
            continue
        cl = cl[~cl.index.duplicated()].copy(); cl.index = cl.index + pd.Timedelta(hours=1)
        p = cl.loc[t.ceil("h") + pd.Timedelta(hours=1):t.ceil("h") + pd.Timedelta(hours=1 + 24 * 7)]
        if len(p) < 2:
            continue
        bad = p[p <= p.iloc[0] * 0.75].index
        if len(bad):
            p = p.loc[:bad[0]]
        r = p.pct_change().dropna(); x = pd.Series(0.05, index=r.index)
        f = fu.reindex(r.index).fillna(0.0) if fu is not None and len(fu) else 0.0
        h = x * r - x * f; h.iloc[0] -= 0.05 * 1e-3; h.iloc[-1] -= 0.05 * 1e-3; h.index = h.index.floor("h")
        pnl = pnl.add(h.groupby(level=0).sum().reindex(idx).fillna(0.0), fill_value=0.0); busy[c] = p.index[-1]
        P.loc[(P.index >= r.index[0].floor("h")) & (P.index <= r.index[-1].floor("h")), c] = 0.05
        used.append({"coin": c, "t": str(t), "trade return %": round(float((1 + r).prod() - 1) * 100, 2)})
    return pnl, P, used


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, ev = stops(idx); _, pos8, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum(); kf = lambda x: 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    full = lambda b: [shp(b, "2022", "2026-09-30"), per(b)]
    book = lambda H: (lambda b: full(b * kf(b)))(CS.portfolio_v5(H)[0])
    def capped(H, extra):
        ph, W, M = CS.portfolio_v5(H); k = kf(ph); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
        w = lambda c: W[c].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
        g = pos8.abs().sum(axis=1).reindex(idx).fillna(0.0) * w("listing short") * m * k * RISK
        for c, gr in extra.items():
            g = g + gr * w(c) * m * k * RISK
        kk = (0.045 / g).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0); H2 = H.copy(); H2["listing short"] *= kk
        for c in extra:
            H2[c] = H2[c] * kk
        return full(CS.portfolio_v5(H2)[0] * k)
    h, P, used = long_sleeve(ev, idx); R = np.array([u["trade return %"] for u in used]); yrs = pd.to_datetime([u["t"] for u in used]).year
    ref = book(V8); r = book(V8.assign(**{"squeeze long": h}))
    pl = {f"{d:+d} days": book(V8.assign(**{"squeeze long": long_sleeve([(c, t + pd.Timedelta(days=d)) for c, t in ev], idx)[0]})) for d in (-14, 14)}
    hu, Pu = RB.venue(list(R16.events().items()) + list(R22.upbit_events().items()), idx); hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx); gf = (hf != 0).astype(float) * 0.05
    ha, Pa = RB.venue(list(R34.events().items()), idx); hh, Ph = RB.venue(list(R42.events().items()), idx)
    HC = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf, "binance add short": ha, "hodler short": hh})
    ex = {"venue listing short": Pu.abs().sum(axis=1), "futures-delisting short": gf, "binance add short": Pa.abs().sum(axis=1), "hodler short": Ph.abs().sum(axis=1)}
    out = {"reference v9.8": ref, "stop-outs": len(ev), "longs traded": len(used), "mean trade %": round(float(R.mean()), 2), "median %": round(float(np.median(R)), 2),
           "hit rate": round(float((R > 0).mean()), 3), "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
           "sleeve 2022 / 23-24 / 25-26": per(h), "corr with event short": round(float(dd(h.loc["2022":]).corr(dd(s8.loc["2022":]))), 3),
           "book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))), "placebo": pl,
           "ALL + add + HODLer": book(HC), "+ squeeze long": book(HC.assign(**{"squeeze long": h})),
           "capped: ALL + add + HODLer": capped(HC, ex), "capped: + squeeze long": capped(HC.assign(**{"squeeze long": h}), {**ex, "squeeze long": P.abs().sum(axis=1)})}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r47_squeeze_long.json").write_text(json.dumps({**out, "trades": used}, indent=1))


if __name__ == "__main__":
    main()

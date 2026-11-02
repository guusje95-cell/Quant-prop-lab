"""v9.9 R44 (research/v99/r44_protocol.json): Coinbase / Upbit listings of coins with only a Bybit perp. Writes results/v99/r44_bybit_venue.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/hub_research", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import bybit_event_shorts as BE
import r16_coinbase as R16
import r22_upbit_r16rules as R22
import r30b_checks as RB
import r32_binance_tag_sleeves as R32
import r34_binance_add as R34
import r42_hodler as R42


def binance_ok(c, T, min_days=0):
    cl, _ = EL._closes(c)
    return cl is not None and ((cl.index > T.floor("h") - pd.Timedelta(hours=3)) & (cl.index <= T.floor("h") + pd.Timedelta(hours=1))).any() and cl.index.min() <= T - pd.Timedelta(days=min_days)


def upbit_all():
    ev = {}
    for f in sorted((ROOT / "research_data/more").glob("upbit_KRW-*_1h.parquet")):
        b = f.name[len("upbit_KRW-"):-len("_1h.parquet")]
        T = pd.DatetimeIndex(pd.read_parquet(f, columns=["close"]).index).min()
        if pd.Timestamp("2021-06-01") <= T <= pd.Timestamp("2026-09-23") and b not in ("BTC", "ETH") and b not in R16.EXCL:
            ev[b] = T
    return ev


def bybit_trade(c, T, need_days=0):
    cl = BE.bybit_closes(c, T - pd.Timedelta(days=max(need_days, 1)), T + pd.Timedelta(days=8))
    if cl is None or not ((cl.index > T.floor("h") - pd.Timedelta(hours=3)) & (cl.index <= T.floor("h") + pd.Timedelta(hours=1))).any():
        return None
    if need_days and cl.index.min() > T - pd.Timedelta(days=need_days) + pd.Timedelta(hours=2):
        return None
    T = T.floor("h"); p = cl.loc[T + pd.Timedelta(hours=1):T + pd.Timedelta(hours=1 + 24 * 7)]
    if len(p) < 2:
        return None
    hit = p[p >= p.iloc[0] * 1.30].index
    if len(hit):
        p = p.loc[:hit[0]]
    r = p.pct_change().dropna(); h = -0.05 * r; h.iloc[0] -= 0.05 * 1e-3; h.iloc[-1] -= 0.05 * 1e-3
    h.index = h.index.floor("h")
    return h.groupby(level=0).sum(), float((1 - r).prod() - 1) * 100


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    CE = R16.events(); UE = upbit_all(); extra = pd.Series(0.0, index=idx); trades = []; last = {}
    cands = [(c, T, "coinbase", 0) for c, T in CE.items() if not binance_ok(c, T)] + [(c, T, "upbit", 7) for c, T in UE.items() if not binance_ok(c, T, 7) and not binance_ok("1000" + c, T, 7)]
    for c, T, v, nd in sorted(cands, key=lambda x: x[1]):
        if c in last and T - last[c] < pd.Timedelta(days=7):
            continue
        res = bybit_trade(c, T, nd)
        if res is None:
            continue
        h, ret = res; extra = extra.add(h.reindex(idx).fillna(0.0), fill_value=0.0); last[c] = T
        trades.append({"coin": c, "venue": v, "t": str(T), "trade return %": round(ret, 2)})
    R = np.array([t["trade return %"] for t in trades]); yrs = pd.to_datetime([t["t"] for t in trades]).year
    hu, _ = RB.venue(list(CE.items()) + list(R22.upbit_events().items()), idx); hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx)
    ha, _ = RB.venue(list(R34.events().items()), idx); hh, _ = RB.venue(list(R42.events().items()), idx)
    HC = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf, "binance add short": ha, "hodler short": hh})
    ref = book(HC); rB = book(HC.assign(**{"venue listing short": hu + extra}))
    out = {"reference ALL + add + HODLer": ref, "new trades": len(trades), "by venue": pd.Series([t["venue"] for t in trades]).value_counts().to_dict() if trades else {},
           "mean trade %": round(float(R.mean()), 2) if len(R) else None, "median %": round(float(np.median(R)), 2) if len(R) else None,
           "hit rate": round(float((R > 0).mean()), 3) if len(R) else None,
           "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))} if len(R) else {},
           "A out-of-sample check passed (mean > 0 and hit > 50%)": bool(len(R) >= 20 and R.mean() > 0 and (R > 0).mean() > 0.5),
           "A as a separate sleeve vs v9.8": book(V8.assign(**{"bybit venue short": extra})), "v9.8": book(V8),
           "B extended venue sleeve": {"book": rB, "pass": bool(rB[0] >= ref[0] + 0.05 and all(rB[1][i] >= ref[1][i] for i in range(3)))}}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r44_bybit_venue.json").write_text(json.dumps({**out, "trades": trades}, indent=1))


if __name__ == "__main__":
    main()

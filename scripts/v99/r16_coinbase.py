"""v9.9 R16 (research/v99/r16_protocol.json): Coinbase first-listing events as Binance-perp trades (sell the news / continuation),
added to the v9.8 event short. Writes results/v99/r16_coinbase.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
EXCL = {"USDT", "USDC", "DAI", "PYUSD", "EURC", "WBTC", "CBETH", "GUSD", "PAX", "USD", "EUR", "GBP"}; COST = 1e-3; SIZE = EL.SIZE


def events():
    D = json.loads((ROOT / "research_data/coinbase_listings/first_trade.json").read_text()); first = {}
    for p in D.values():
        if p["first_trade_utc"] and p["base"] not in EXCL:
            t = pd.Timestamp(p["first_trade_utc"]); first[p["base"]] = min(first.get(p["base"], t), t)
    return {c: t for c, t in first.items() if pd.Timestamp("2022-01-01") <= t <= pd.Timestamp("2026-09-23")}


def trades(E, idx, mode):
    pnl = pd.Series(0.0, index=idx); used = []
    for coin, T in sorted(E.items(), key=lambda x: x[1]):
        cl, fu = EL._closes(coin)
        if cl is None:
            continue
        cl = cl.copy(); cl.index = cl.index + pd.Timedelta(hours=1)                         # stamp = time the close is known
        T = T.floor("h")
        if not ((cl.index > T - pd.Timedelta(hours=3)) & (cl.index <= T + pd.Timedelta(hours=1))).any():
            continue                                                                         # no Binance perp trading at the listing
        side, hold = (-1, 24 * 7) if mode == "A" else (1, 24)
        p = cl.loc[T + pd.Timedelta(hours=1):T + pd.Timedelta(hours=1 + hold)]
        if len(p) < 2:
            continue
        r = p.pct_change().dropna(); x = pd.Series(side * SIZE, index=r.index)
        if mode == "A":
            hit = p[p >= p.iloc[0] * (1 + EL.STOP)].index
            if len(hit):
                x = x.loc[:hit[0]]; r = r.loc[:hit[0]]
        f = fu.reindex(r.index).fillna(0.0) if fu is not None and len(fu) else 0.0
        h = x * r - x * f; h.iloc[0] -= SIZE * COST; h.iloc[-1] -= SIZE * COST
        h.index = h.index.floor("h"); pnl = pnl.add(h.groupby(level=0).sum().reindex(idx).fillna(0.0), fill_value=0.0)
        used.append({"coin": coin, "t": str(T), "trade return %": round(float((1 + side * r).prod() - 1) * 100, 2)})
    return pnl, used


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx)
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    b0 = unit(CS.portfolio_v5(V7.assign(**{"listing short": s8}))[0]); ref = [shp(b0, "2022", "2026-09-30"), per(b0)]
    E = events(); out = {"reference v9.8": ref, "coinbase listings 2022-26 (non-stable)": len(E)}
    for k, name in (("A", "A sell the news (short 7 d)"), ("B", "B continuation (long 24 h)")):
        h, used = trades(E, idx, k); R = np.array([u["trade return %"] for u in used])
        b = unit(CS.portfolio_v5(V7.assign(**{"listing short": s8 + h}))[0]); r = [shp(b, "2022", "2026-09-30"), per(b)]
        out[name] = {"events traded": len(used), "mean trade %": round(float(R.mean()), 2) if len(R) else None,
                     "median %": round(float(np.median(R)), 2) if len(R) else None, "hit rate": round(float((R > 0).mean()), 3) if len(R) else None,
                     "by year (n, mean %)": {y: [int(((pd.to_datetime([u["t"] for u in used]).year) == y).sum()),
                                                 round(float(R[(pd.to_datetime([u["t"] for u in used]).year) == y].mean()), 2) if ((pd.to_datetime([u["t"] for u in used]).year) == y).any() else None] for y in range(2022, 2027)},
                     "book": r, "pass": bool(len(used) >= 30 and r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))), "trades": used}
        print(name, {k2: v for k2, v in out[name].items() if k2 != "trades"}, flush=True)
    (ROOT / "results/v99/r16_coinbase.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

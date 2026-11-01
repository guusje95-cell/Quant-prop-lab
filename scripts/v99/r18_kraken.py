"""v9.9 R18 (research/v99/r18_protocol.json): Kraken first listings as sell-the-news shorts (R16 A rules), alone and on top of R16.
Writes results/v99/r18_kraken.json."""
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


def kraken_events():
    D = json.loads((ROOT / "research_data/kraken_listings/first_trade.json").read_text()); first = {}
    for p in D.values():
        if p["first_trade_utc"] and p["base"] not in R16.EXCL:
            t = pd.Timestamp(p["first_trade_utc"]); first[p["base"]] = min(first.get(p["base"], t), t)
    return {c: t for c, t in first.items() if pd.Timestamp("2022-01-01") <= t <= pd.Timestamp("2026-09-23")}


def trades_list(ev, idx):
    """R16 A on a list of (coin, T); an event within 7 days after an earlier event of the same coin is skipped"""
    pnl = pd.Series(0.0, index=idx); used = []; last = {}
    for coin, T in sorted(ev, key=lambda x: x[1]):
        if coin in last and T - last[coin] < pd.Timedelta(days=7):
            continue
        h, u = R16.trades({coin: T}, idx, "A")
        if u:
            pnl = pnl + h; used += u; last[coin] = T
    return pnl, used


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx)
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda s: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(V7.assign(**{"listing short": s}))[0]))
    ref = book(s8); KE = kraken_events(); CE = R16.events()
    hc, _ = trades_list(list(CE.items()), idx); ref16 = book(s8 + hc)
    hk, uk = trades_list(list(KE.items()), idx); hb, ub = trades_list(list(CE.items()) + list(KE.items()), idx)
    R = np.array([u["trade return %"] for u in uk]); yrs = pd.to_datetime([u["t"] for u in uk]).year
    rA, rB = book(s8 + hk), book(s8 + hb)
    out = {"reference v9.8": ref, "reference v9.8 + R16 A": ref16, "kraken listings 2022-26": len(KE),
           "A Kraken sell the news": {"events traded": len(uk), "mean trade %": round(float(R.mean()), 2), "median %": round(float(np.median(R)), 2),
                                      "hit rate": round(float((R > 0).mean()), 3), "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
                                      "overlap with Coinbase events (same coin within 7 days)": int(sum(1 for c, t in KE.items() if c in CE and abs(CE[c] - t) < pd.Timedelta(days=7))),
                                      "book": rA, "pass": bool(len(uk) >= 30 and rA[0] >= ref[0] + 0.05 and all(rA[1][i] >= ref[1][i] for i in range(3)))},
           "B Coinbase + Kraken": {"events traded": len(ub), "book": rB, "pass": bool(rB[0] >= ref16[0] + 0.05 and all(rB[1][i] >= ref16[1][i] for i in range(3)))},
           "kraken trades": uk}
    print(json.dumps({k: v for k, v in out.items() if k != "kraken trades"}, indent=1))
    (ROOT / "results/v99/r18_kraken.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

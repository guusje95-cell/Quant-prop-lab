"""v9.9 R19 (research/v99/r19_protocol.json): Hyperliquid perp listings as sell-the-news shorts on Binance (R16 A rules).
Writes results/v99/r19_hl_listings.json."""
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
import r18_kraken as R18


def hl_events():
    D = json.loads((ROOT / "research_data/hyperliquid_listings/first_funding.json").read_text()); ev = {}
    for name, v in D.items():
        if not v["first_funding_utc"]:
            continue
        coin = name[1:] if name.startswith("k") and name[1:].isupper() else name               # kPEPE -> PEPE (thousand-unit perps)
        T = pd.Timestamp(v["first_funding_utc"])
        if not (pd.Timestamp("2023-07-01") <= T <= pd.Timestamp("2026-09-23")) or coin in R16.EXCL:
            continue
        cl, _ = EL._closes(coin) if coin not in ("PEPE", "SHIB", "BONK", "FLOKI") else EL._closes("1000" + coin)
        if cl is None or cl.index.min() > T - pd.Timedelta(days=7):
            continue                                                                            # Binance perp must be >= 7 days old
        ev[coin if coin not in ("PEPE", "SHIB", "BONK", "FLOKI") else "1000" + coin] = T
    return ev


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx)
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda s: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(V7.assign(**{"listing short": s}))[0]))
    ref = book(s8); E = hl_events(); CE = R16.events()
    h, used = R18.trades_list(list(E.items()), idx); hc, _ = R18.trades_list(list(CE.items()), idx); hb, _ = R18.trades_list(list(CE.items()) + list(E.items()), idx)
    R = np.array([u["trade return %"] for u in used]); yrs = pd.to_datetime([u["t"] for u in used]).year; r = book(s8 + h)
    out = {"reference v9.8": ref, "HL listings in window with a >= 7-day-old Binance perp": len(E), "events traded": len(used),
           "mean trade %": round(float(R.mean()), 2), "median %": round(float(np.median(R)), 2), "hit rate": round(float((R > 0).mean()), 3),
           "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
           "book": r, "pass": bool(len(used) >= 30 and r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))),
           "reported: v9.8 + R16 A": book(s8 + hc), "reported: v9.8 + R16 A + R19": book(s8 + hb), "trades": used}
    print(json.dumps({k: v for k, v in out.items() if k != "trades"}, indent=1))
    (ROOT / "results/v99/r19_hl_listings.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

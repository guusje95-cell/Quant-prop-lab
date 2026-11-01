"""v9.9 R37 (research/v99/r37_protocol.json): Bithumb first listings as a sell-the-news sleeve. Writes results/v99/r37_bithumb.json."""
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
import r30b_checks as RB
import r32_binance_tag_sleeves as R32


def events():
    D = json.loads((ROOT / "research_data/bithumb_listings/first_trade.json").read_text()); f = {}
    for v in D.values():
        if v["base"] in R16.EXCL:
            continue
        t = pd.Timestamp(v["first_trade_utc"]); f[v["base"]] = min(f.get(v["base"], t), t)
    ev = {}
    for b, t in f.items():
        if not (pd.Timestamp("2022-01-01") <= t <= pd.Timestamp("2026-09-23")):
            continue
        for c in (b, "1000" + b):
            cl, _ = EL._closes(c)
            if cl is not None and cl.index.min() <= t - pd.Timedelta(days=7):
                ev[c] = t; break
    return ev


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    ref = book(V8); E = events(); CE = R16.events(); UE = R22.upbit_events(); h, _ = RB.venue(list(E.items()), idx)
    _, used = R16.trades(E, idx, "A"); R = np.array([u["trade return %"] for u in used]); yrs = pd.to_datetime([u["t"] for u in used]).year
    r = book(V8.assign(**{"bithumb listing short": h}))
    hu, _ = RB.venue(list(CE.items()) + list(UE.items()), idx); hk, _ = RB.venue(list(CE.items()) + list(UE.items()) + list(E.items()), idx); hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx)
    HA = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf})
    out = {"reference v9.8": ref, "bithumb listings 2022-26 (perp >= 7 d)": len(E), "traded": len(used),
           "overlap with Upbit (same coin within 7 days)": int(sum(1 for c, t in E.items() if c in UE and abs(UE[c] - t) < pd.Timedelta(days=7))),
           "mean trade %": round(float(R.mean()), 2), "median %": round(float(np.median(R)), 2), "hit rate": round(float((R > 0).mean()), 3),
           "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
           "sleeve 2022 / 23-24 / 25-26": per(h), "book": r, "pass": bool(len(used) >= 30 and r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))),
           "placebo": {f"{d:+d} days": book(V8.assign(**{"bithumb listing short": RB.venue([(c, t + pd.Timedelta(days=d)) for c, t in E.items()], idx)[0]})) for d in (-60, 60)},
           "ALL": book(HA), "B ALL with Bithumb in the venue sleeve": book(HA.assign(**{"venue listing short": hk}))}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r37_bithumb.json").write_text(json.dumps({**out, "trades": used}, indent=1))


if __name__ == "__main__":
    main()

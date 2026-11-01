"""v9.9 R22 (research/v99/r22_protocol.json): Upbit listings with the R16 sell-the-news rules. Writes results/v99/r22_upbit.json."""
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


def upbit_events():
    ev = {}
    for f in sorted((ROOT / "research_data/more").glob("upbit_KRW-*_1h.parquet")):
        base = f.name[len("upbit_KRW-"):-len("_1h.parquet")]
        T = pd.DatetimeIndex(pd.read_parquet(f, columns=["close"]).index).min()
        if T < pd.Timestamp("2021-06-01") or T > pd.Timestamp("2026-09-23") or base in ("BTC", "ETH") or base in R16.EXCL:
            continue
        for c in (base, "1000" + base):
            cl, _ = EL._closes(c)
            if cl is not None and cl.index.min() <= T - pd.Timedelta(days=7):
                ev[c] = T; break
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
    ref = book(s8); UE = upbit_events(); CE = R16.events()
    hu, uu = R18.trades_list(list(UE.items()), idx); hc, _ = R18.trades_list(list(CE.items()), idx); hb, ub = R18.trades_list(list(CE.items()) + list(UE.items()), idx)
    ref16 = book(s8 + hc); rA = book(s8 + hu); rB = book(s8 + hb); R = np.array([u["trade return %"] for u in uu]); yrs = pd.to_datetime([u["t"] for u in uu]).year
    out = {"reference v9.8": ref, "reference v9.8 + R16 A": ref16, "upbit events": len(UE), "traded": len(uu), "mean trade %": round(float(R.mean()), 2),
           "median %": round(float(np.median(R)), 2), "hit rate": round(float((R > 0).mean()), 3),
           "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
           "alone": {"book": rA, "pass": bool(rA[0] >= ref[0] + 0.05 and all(rA[1][i] >= ref[1][i] for i in range(3)))},
           "added to R16 A": {"events traded": len(ub), "book": rB, "pass": bool(rB[0] >= ref16[0] + 0.05 and all(rB[1][i] >= ref16[1][i] for i in range(3)))}}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r22_upbit.json").write_text(json.dumps({**out, "trades": uu}, indent=1))


if __name__ == "__main__":
    main()

"""v9.9 R30 (research/v99/r30_protocol.json): Coinbase (+ Upbit) sell-the-news shorts as a separate sleeve. Writes results/v99/r30_venue_sleeve.json."""
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
import r22_upbit_r16rules as R22


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    ref = book(V8); CE = R16.events(); UE = R22.upbit_events()
    hc, _ = R18.trades_list(list(CE.items()), idx); hb, _ = R18.trades_list(list(CE.items()) + list(UE.items()), idx)
    out = {"reference v9.8": ref, "reference v9.8 + R16 A inside the event sleeve": book(V8.assign(**{"listing short": s8 + hc})),
           "sleeve Coinbase + Upbit 2022 / 23-24 / 25-26": per(hb), "sleeve Coinbase only": per(hc),
           "corr with event sleeve (daily)": round(float(dd(hb.loc["2022":]).corr(dd(s8.loc["2022":]))), 3)}
    for name, h in (("A Coinbase + Upbit, separate sleeve", hb), ("B Coinbase only, separate sleeve", hc)):
        r = book(V8.assign(**{"venue listing short": h})); out[name] = {"book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    print(json.dumps({k: v for k, v in out.items() if not k.startswith(("A ", "B "))}, indent=1))
    (ROOT / "results/v99/r30_venue_sleeve.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

"""v9.9 R7c (diagnostics of R7 A, no selection): placebo dates for the merged variant, per-category split, and R7 A on top of the
current best candidate (ALL + add + HODLer, event short with unlocks). Writes results/v99/r7c_checks.json."""
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
import r34_binance_add as R34
import r42_hodler as R42
import r7b_unlocks as U
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
dd = lambda x: x.groupby(x.index.floor("D")).sum(); unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(x, a, z):
    d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), [shp(b, "2022", "2022"), shp(b, "2023", "2024"), shp(b, "2025", "2026-09-30")]])(unit(CS.portfolio_v5(H)[0]))
E = U.events(); sA = EL.pnl(idx, pre_cap=U.hook_for(E, idx))[0]
out = {"reference v9.8": book(V8), "A merged": book(V8.assign(**{"listing short": sA})),
       "A placebo": {f"{k:+d} days": book(V8.assign(**{"listing short": EL.pnl(idx, pre_cap=U.hook_for([(c, d + pd.Timedelta(days=k), p, ca) for c, d, p, ca in E], idx))[0]})) for k in (-90, -60, -30, 30, 60, 90)},
       "A insiders + private sale only": book(V8.assign(**{"listing short": EL.pnl(idx, pre_cap=U.hook_for([e for e in E if e[3] in ("insiders", "privateSale")], idx))[0]}))}
hu, _ = RB.venue(list(R16.events().items()) + list(R22.upbit_events().items()), idx); hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx)
ha, _ = RB.venue(list(R34.events().items()), idx); hh, _ = RB.venue(list(R42.events().items()), idx)
HC = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf, "binance add short": ha, "hodler short": hh})
out["ALL + add + HODLer"] = book(HC); out["ALL + add + HODLer with R7 A in the event short"] = book(HC.assign(**{"listing short": sA}))
print(json.dumps(out, indent=1)); (ROOT / "results/v99/r7c_checks.json").write_text(json.dumps(out, indent=1))

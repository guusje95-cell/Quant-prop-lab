"""v9.9 R28 (diagnostic + 9 removal trials, research/v99/r28_protocol.json): leave-one-sleeve-out of v9.8. Writes results/v99/r28_loo.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
dd = lambda x: x.groupby(x.index.floor("D")).sum()
unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(x, a, z):
    d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
ref = book(V8); out = {"reference v9.8": ref, "sleeve alone 2022 / 23-24 / 25-26": {c: per(V8[c]) for c in V8.columns}, "without": {}}
for c in V8.columns:
    r = book(V8.drop(columns=c)); out["without"][c] = {"book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
    print(c, out["without"][c], flush=True)
(ROOT / "results/v99/r28_loo.json").write_text(json.dumps(out, indent=1))

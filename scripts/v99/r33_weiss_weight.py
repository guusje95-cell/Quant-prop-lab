"""v9.9 R33 (research/v99/r33_protocol.json): Weiss expiry at full weight. Writes results/v99/r33_weiss_weight.json."""
import functools
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
dd = lambda x: x.groupby(x.index.floor("D")).sum(); unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(x, a, z):
    d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
full = lambda b: [shp(b, "2022", "2026-09-30"), [shp(b, "2022", "2022"), shp(b, "2023", "2024"), shp(b, "2025", "2026-09-30")]]
ref = full(unit(CS.portfolio_v5(V8)[0])); orig = CS.v5_weights
CS.v5_weights = functools.partial(orig, weiss_scale=1.0); r = full(unit(CS.portfolio_v5(V8)[0])); CS.v5_weights = orig
out = {"reference v9.8": ref, "Weiss full weight": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
print(out); (ROOT / "results/v99/r33_weiss_weight.json").write_text(json.dumps(out, indent=1))

"""Gen448 (config/gen448_protocol.json): Weiss expiry at full weight in v9.6. Writes results/gen448.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, _ = LL.pnl(idx); H = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(H)[0]); REF = (shp(v96), per(v96))
orig = CS.v5_weights
CS.v5_weights = lambda D, sleeves=CS.V5_SLEEVES, weiss_scale=0.5: orig(D, sleeves, weiss_scale=1.0)
b = unit(CS.portfolio_v5(H)[0]); CS.v5_weights = orig; r = [shp(b), per(b)]
out = {"reference v9.6 A..Z": [REF[0], REF[1]], "book Weiss full weight": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen448.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))

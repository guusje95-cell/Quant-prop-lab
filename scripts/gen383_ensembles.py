"""Gen383 (config/gen383_protocol.json). Writes results/gen383.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import alt_kimchi as AK
END = "2026-09-30"
dd = lambda h: h.groupby(h.index.floor("D")).sum()
shp = lambda h, a="2022", z=END: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
base = pd.read_parquet(ROOT / "results/k1_sleeves.parquet")
bh = pd.read_parquet(ROOT / "results/gen380_basket_hourly.parquet")["basket"].reindex(base.index).fillna(0.0)
B0 = base.assign(**{"diversifier basket": bh}); v91 = unit(CS.portfolio_v5(B0)[0]); REF = (shp(v91), per(v91))
te = (sum(CS.trend4h(n_in=n, n_out=n // 2).loc[:END + " 23:00"] for n in (15, 20, 30)) / 3).reindex(base.index).fillna(0.0)
def ak(t):
    w = AK.weights(END + " 23:00", th=t); return CS._from_daily_weights(w, list(w.columns), 5).loc[:END + " 23:00"]
ke = (sum(ak(t) for t in (0.75, 1.0, 1.25)) / 3).reindex(base.index).fillna(0.0)
chk = round(float(np.corrcoef(dd(ak(1.0).reindex(base.index).fillna(0.0)).loc["2022":], dd(base["alt kimchi"]).loc["2022":])[0, 1]), 4)
T = {"A trend 4h ensemble": B0.assign(**{"trend 4h": te}), "B alt kimchi ensemble": B0.assign(**{"alt kimchi": ke}), "C both": B0.assign(**{"trend 4h": te, "alt kimchi": ke})}
out = {"reference v9.1": [REF[0], REF[1]], "check alt kimchi th=1.0 vs book sleeve (corr)": chk, "trials": {}}
for k, H in T.items():
    b = unit(CS.portfolio_v5(H)[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"2022-26 [periods]": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
print(json.dumps(out, indent=1)); (ROOT / "results/gen383.json").write_text(json.dumps(out, indent=1))

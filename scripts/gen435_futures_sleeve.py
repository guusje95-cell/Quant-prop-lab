"""Gen435 (config/gen435_protocol.json): the futures book as a sleeve in v9.6. Writes results/gen435.json."""
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
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0])
fb = pd.read_parquet(ROOT / "results/futures_book_rebuild.parquet")["book"]; fb.index = pd.DatetimeIndex(fb.index).normalize()
h = pd.Series(0.0, index=idx); t = fb.index + pd.Timedelta(hours=21); m = t.isin(idx); h.loc[t[m]] = fb.to_numpy()[m]
h = h - 0.04 / (365 * 24)                                                 # funding drag, spread over every hour
s = h.reindex(idx).fillna(0.0); b = unit(CS.portfolio_v5(V6.assign(**{"futures book": s}))[0]); r = [shp(b), per(b)]
REF_R = (3.161, [2.775, 3.919, 2.576])
out = {"reference v9.6 (research)": REF_R, "reference v9.6 (live timing)": [shp(v96), per(v96)], "sleeve (after drag)": per(s),
       "corr with v9.6 (daily)": round(float(dd(s).loc["2022":].corr(dd(v96).loc["2022":])), 3), "book": r,
       "pass": bool(r[0] >= REF_R[0] + 0.05 and all(r[1][i] >= REF_R[1][i] for i in range(3)))}
(ROOT / "results/gen435.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))

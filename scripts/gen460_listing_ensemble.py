"""Gen460 (config/gen460_protocol.json): listing-short neighbourhood ensemble (hold x stop). Writes results/gen460.json."""
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
ls, _, EV = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
CF = {s[:-4]: (c, f) for s, t0, c, f in EV}
def var_pnl(hold, stop):
    LL.HOLD, LL.STOP = hold, stop; pos = LL.positions(idx, EV); out = pd.Series(0.0, index=idx)
    for n in pos.columns:
        c, f = CF[n]; p = pos[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * LL.COST_BP / 1e4
    return out
S = {(h, s): var_pnl(h, s) for h in (14, 30, 60) for s in (0.20, 0.30, 0.50)}
LL.HOLD, LL.STOP = 30, 0.30
ens = sum(S.values()) / len(S)
b = unit(CS.portfolio_v5(V7.assign(**{"listing short": ens}))[0]); r = [shp(b), per(b)]
out = {"reference v9.7": [REF[0], REF[1]], "variants": {f"hold {h} stop {int(s * 100)}%": per(v) for (h, s), v in S.items()}, "ensemble sleeve": per(ens),
       "single (30 d, 30%) sleeve": per(ls), "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen460.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

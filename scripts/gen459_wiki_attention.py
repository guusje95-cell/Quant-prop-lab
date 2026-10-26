"""Gen459 (config/gen459_protocol.json): Wikipedia attention - relative across the 6 majors, and a BTC/ETH froth member. Writes results/gen459.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\nout = {")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
shp, per, unit, CS, C6, pnl, days = (g[k] for k in ("shp", "per", "unit", "CS", "C6", "pnl", "days"))
import listing_live as LL
import basket_live as BL
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
ls, _, _ = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
W = pd.read_parquet(ROOT / "research_data/attention/wiki_pageviews.parquet"); W.index = pd.DatetimeIndex(W.index)
z = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
att = np.log(W.where(W > 0).rolling(7, min_periods=5).mean()).reindex(days).shift(1)   # day d views known after d -> row d + 1
Z = pd.DataFrame({c: z(att[c], 90) for c in C6}); Zd = Z.sub(Z.mean(axis=1), axis=0)
WA = (-0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0)
sA = pnl(WA).reindex(idx).fillna(0.0)
bA = unit(CS.portfolio_v5(V7.assign(**{"relative attention 6": sA}))[0]); rA = [shp(bA), per(bA)]
fz = z(np.log(W[["BTC", "CRYPTO"]].sum(axis=1).where(lambda s: s > 0).rolling(7, min_periods=5).mean()), 365).reindex(BL.DAYS).shift(1)
mk = lambda: pd.DataFrame({"BTC": -0.125 * fz.clip(-2, 2) / 2, "ETH": -0.125 * fz.clip(-2, 2) / 2}).fillna(0.0)
bk0, _ = BL.basket(idx); r0 = unit(CS.portfolio_v5(V7.assign(**{"diversifier basket": bk0}))[0]); REF2 = (shp(r0), per(r0))
base = list(BL.MEMBERS); BL.BUILD["attention froth"] = mk; BL.MEMBERS = base + ["attention froth"]; bk, _ = BL.basket(idx); BL.MEMBERS = base
bB = unit(CS.portfolio_v5(V7.assign(**{"diversifier basket": bk}))[0]); rB = [shp(bB), per(bB)]
mB = CS._from_daily_weights(mk().reindex(BL.DAYS).fillna(0.0), ["BTC", "ETH"], 5).reindex(idx).fillna(0.0)
ok = lambda r, R: bool(r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3)))
out = {"reference v9.7": [REF[0], REF[1]], "reference rebuilt basket": [REF2[0], REF2[1]],
       "A relative attention 6": {"sleeve": per(sA), "corr relative crowding": round(float(sA.corr(V7["relative crowding 6"])), 2), "book": rA, "pass": ok(rA, REF)},
       "B attention froth member": {"member": per(mB), "basket": per(bk), "book": rB, "pass": ok(rB, REF) and ok(rB, REF2)}}
(ROOT / "results/gen459.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

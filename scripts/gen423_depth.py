"""Gen423 (config/gen423_protocol.json): order-book depth imbalance. Writes results/gen423.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\nout = {")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
shp, per, unit, CS, V0, C6, rc6, a, bsm, pnl, days = (g[k] for k in ("shp", "per", "unit", "CS", "V", "C6", "rc6", "a", "bsm", "pnl", "days"))
import basket_live as BL
V = V0.assign(**{"relative crowding 6": (rc6 + a + bsm) / 3}); v95 = unit(CS.portfolio_v5(V)[0]); REF = (shp(v95), per(v95))
z = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
def I2(c):
    d = pd.read_parquet(ROOT / f"research_data/binance_depth/{c}USDT_depth_1h.parquet")["I2"]
    return BL.daily(d, "mean")                                   # day d -> row d + 1 (BL convention, on BL.DAYS)
def member():
    return pd.DataFrame({c: 0.125 * z(I2(c), 90).clip(-2, 2) / 2 for c in ("BTC", "ETH")})
bk0, _ = BL.basket(V.index); r0 = unit(CS.portfolio_v5(V.assign(**{"diversifier basket": bk0}))[0]); REF2 = (shp(r0), per(r0))
base = list(BL.MEMBERS); BL.BUILD["depth"] = member; BL.MEMBERS = base + ["depth"]; bk, _ = BL.basket(V.index); BL.MEMBERS = base
bA = unit(CS.portfolio_v5(V.assign(**{"diversifier basket": bk}))[0]); rA = [shp(bA), per(bA)]
mA = CS._from_daily_weights(member().reindex(BL.DAYS).fillna(0.0), ["BTC", "ETH"], 5).reindex(V.index).fillna(0.0)
# B: same timing convention as the relative crowding sleeve (daily() value of day d at row d + 1, then pnl()'s one-day shift)
Z = pd.DataFrame({c: z(I2(c), 90) for c in C6}).reindex(days); Zd = Z.sub(Z.mean(axis=1), axis=0)
WB = (0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0); sB = pnl(WB).reindex(V.index).fillna(0.0)
bB = unit(CS.portfolio_v5(V.assign(**{"relative depth 6": sB}))[0]); rB = [shp(bB), per(bB)]
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
out = {"reference v9.5": [REF[0], REF[1]], "reference rebuilt basket": [REF2[0], REF2[1]],
       "A depth imbalance BTC/ETH": {"member": per(mA), "basket": per(bk), "book": rA, "pass": bool(ok(rA, REF) and ok(rA, REF2))},
       "B relative depth imbalance 6": {"sleeve": per(sB), "corr rc6": round(float(sB.corr(V["relative crowding 6"])), 2), "book": rB, "pass": bool(ok(rB, REF))}}
(ROOT / "results/gen423.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))

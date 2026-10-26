"""Gen441 (config/gen441_protocol.json): re-run the Gen391 stepwise basket selection with the newer candidates. Writes results/gen441.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen390_breadth_regime.py").read().split("\nref_book = pd.read_parquet(ROOT")[0]
g = {"__file__": str(ROOT / "scripts/gen390_breadth_regime.py")}; exec(compile(src, "g390", "exec"), g)
POOL, dd, shp, per, unit, END, K1 = (g[k] for k in ("POOL", "dd", "shp", "per", "unit", "END", "K1"))
import crypto_sleeves as CS
import listing_live as LL
import basket_live as BL
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
# ---- new candidates (as registered in their own protocols)
g440 = {"__file__": str(ROOT / "scripts/gen440_follow_froth.py")}; exec(compile(open(ROOT / "scripts/gen440_follow_froth.py").read().split("\nls, _, _ = LL.pnl(idx)")[0], "g440", "exec"), g440)
g421 = {"__file__": str(ROOT / "scripts/gen421_coinm.py")}; exec(compile(open(ROOT / "scripts/gen421_coinm.py").read().split("\nbk0, _ = BL.basket")[0], "g421", "exec"), g421)
g434 = {"__file__": str(ROOT / "scripts/gen434_listing_pace.py")}; exec(compile(open(ROOT / "scripts/gen434_listing_pace.py").read().split("\nbk0, _ = BL.basket(idx)")[0], "g434", "exec"), g434)
g414 = {"__file__": str(ROOT / "scripts/gen414_watchlist.py")}; exec(compile(open(ROOT / "scripts/gen414_watchlist.py").read().split("\n# A\n")[0] + "\n" + open(ROOT / "scripts/gen414_watchlist.py").read().split("# B\n")[1].split("\nbk0, _ = BL.basket")[0], "g414", "exec"), g414)
to_h = lambda w: CS._from_daily_weights(w.reindex(BL.DAYS).fillna(0.0), list(w.columns), 5).reindex(idx).fillna(0.0)
NEW = {"Gen440 follow alt premium froth": to_h(g440["mk"](g440["zser"]())()), "Gen281 CME basis level": to_h(g414["cme"]()),
       "Gen421 A COIN-M leverage build-up": to_h(g421["coinm_lev"]()), "Gen434 A listing pace": to_h(g434["member"]())}
P = {**POOL, **NEW}
D = pd.DataFrame({k: dd(v) for k, v in P.items()}).loc["2022":END].fillna(0.0); D24 = D.loc[:"2024"]
K1d = dd(K1).loc["2022":"2024"]
cand = [k for k in D if abs(float(pd.concat([D24[k], K1d], axis=1).corr().iloc[0, 1])) < 0.3 and D24[k].std() > 0]
def bsr(keys):
    x = (D24[keys] / D24[keys].std()).sum(axis=1); return float(x.mean() / x.std() * np.sqrt(365))
kept, cur, steps = [], -9.0, []
while True:
    best = max(((k, bsr(kept + [k])) for k in cand if k not in kept), key=lambda t: t[1], default=(None, -9))
    if best[0] is None or best[1] < cur + 0.05:
        break
    kept.append(best[0]); cur = best[1]; steps.append([best[0], round(cur, 3)])
def basket(keys):
    sdv = D24[keys].std(); bh = sum(P[k].reindex(idx).fillna(0.0) / sdv[k] for k in keys); return bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
G391 = [s[0] for s in json.loads((ROOT / "results/gen391.json").read_text())["steps (member, basket 2022-24 Sharpe)"]]
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0]); REF = (shp(v96), per(v96))
r0 = unit(CS.portfolio_v5(V6.assign(**{"diversifier basket": basket(G391)}))[0]); REF2 = (shp(r0), per(r0))
bh = basket(kept); b = unit(CS.portfolio_v5(V6.assign(**{"diversifier basket": bh}))[0]); r = [shp(b), per(b)]
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
out = {"reference v9.6 (live timing)": [REF[0], REF[1]], "reference like-for-like (Gen391 members from the pool)": [REF2[0], REF2[1]],
       "pool size": len(P), "candidates": len(cand), "new candidates passing the corr filter": [k for k in NEW if k in cand],
       "steps": steps, "same members as Gen391": sorted(kept) == sorted(G391), "basket": per(bh), "book": r, "pass": bool(ok(r, REF) and ok(r, REF2))}
(ROOT / "results/gen441.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

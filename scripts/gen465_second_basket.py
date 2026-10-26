"""Gen465 (config/gen465_protocol.json, FLAGGED): a second basket of the weak-but-positive new signals. Writes results/gen465.json."""
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
def load(script, cut, name):
    g = {"__file__": str(ROOT / "scripts" / script)}; exec(compile(open(ROOT / "scripts" / script).read().split(cut)[0], script, "exec"), g); return g[name]
g440 = {"__file__": str(ROOT / "scripts/gen440_follow_froth.py")}; exec(compile(open(ROOT / "scripts/gen440_follow_froth.py").read().split("\nls, _, _ = LL.pnl(idx)")[0], "g440", "exec"), g440)
M = {"follow froth": g440["mem_pnl"](g440["zser"]())}
M["relative crowding top-20"] = load("gen447_rc_pit20.py", "\nb = unit(CS.portfolio_v5(V6", "s")
M["new-coin crowding"] = load("gen464_newcoin_rc.py", "\nb = unit(CS.portfolio_v5(V7", "s_")
M = {k: v.reindex(idx).fillna(0.0) for k, v in M.items()}
D24 = pd.DataFrame({k: dd(v) for k, v in M.items()}).loc["2022":"2024"]
bh = sum(M[k] / D24[k].std() for k in M); bh = unit(bh)
ls, _, _ = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
b = unit(CS.portfolio_v5(V7.assign(**{"second basket": bh}))[0]); r = [shp(b), per(b)]
C = pd.DataFrame({k: dd(v) for k, v in M.items()}).loc["2022":].corr().round(2)
out = {"reference v9.7": [REF[0], REF[1]], "members": {k: per(v) for k, v in M.items()}, "member correlations": C.to_dict(),
       "second basket": per(bh), "by year": {str(y): shp(bh, str(y), str(y)) for y in range(2022, 2027)}, "corr with the diversifier basket": round(float(dd(bh).corr(dd(V7["diversifier basket"]))), 2),
       "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
bh.to_frame("second basket").to_parquet(ROOT / "results/gen465_basket_hourly.parquet")
(ROOT / "results/gen465.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

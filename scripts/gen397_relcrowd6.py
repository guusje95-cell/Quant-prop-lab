"""Gen397 (config/gen397_protocol.json, flagged). Writes results/gen397.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen396_relcrowd.py").read().split("\nC3 = (")[0]
g = {"__file__": str(ROOT / "scripts/gen396_relcrowd.py")}; exec(compile(src, "g396", "exec"), g)
dd, shp, per, unit, END, CS, V, REF, sleeve, z, daily, B, pnl, days = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "REF", "sleeve", "z", "daily", "B", "pnl", "days"))
src0 = open(ROOT / "scripts/gen390_breadth_regime.py").read().split("\nref_book = pd.read_parquet(ROOT")[0]
g0 = {"__file__": str(ROOT / "scripts/gen390_breadth_regime.py")}; exec(compile(src0, "g390b", "exec"), g0); POOL = g0["POOL"]
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"); rc6 = sleeve(C6)
kept = [s[0] for s in json.loads((ROOT / "results/gen391.json").read_text())["steps (member, basket 2022-24 Sharpe)"]]
P = {k: POOL[k].reindex(V.index).fillna(0.0) for k in kept}; P["relative crowding 6"] = rc6
sdv = pd.DataFrame({k: dd(v) for k, v in P.items()}).loc["2022":"2024"].std(); bh = sum(P[k] / sdv[k] for k in P); bh = bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
T = {"A 6-coin RC in the basket": V.assign(**{"diversifier basket": bh}), "B 6-coin RC as its own sleeve": V.assign(**{"relative crowding 6": rc6})}
out = {"reference v9.3": [REF[0], REF[1]], "6-coin sleeve": per(rc6), "trials": {}}
for k, H in T.items():
    b = unit(CS.portfolio_v5(H)[0]); d = dd(b).loc["2022":END]
    out["trials"][k] = {"2022-24": shp(b, "2022", "2024"), "book": [shp(b), per(b)], "by year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.groupby(d.index.year)}}
    if k.startswith("A"):
        out["trials"][k]["basket"] = per(bh)
ch = max(out["trials"], key=lambda k: out["trials"][k]["2022-24"]); r = out["trials"][ch]["book"]
out["chosen"] = ch; out["pass"] = bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))
# descriptive: point-in-time top-6 by trailing 30-day volume among pack coins (monthly)
pk = B.coins(); qv = pd.DataFrame({c: B.k5(c).quote_volume.resample("1D").sum() for c in pk}).reindex(days)
mem = (qv.rolling(30, min_periods=20).sum().shift(1).rank(axis=1, ascending=False) <= 6)
mem = mem[~mem.index.to_period("M").duplicated()].reindex(days).ffill().fillna(False)
def relp(col):
    Z = pd.DataFrame({c: z(daily(B.metrics(c)[col], "mean"), 90) for c in pk}).where(mem)
    Zd = Z.sub(Z.mean(axis=1), axis=0); return (-0.15 * Zd.clip(-2, 2) / 2).fillna(0.0)
rcp = ((pnl(relp("count_toptrader_long_short_ratio")) + pnl(relp("count_long_short_ratio"))) / 2).reindex(V.index).fillna(0.0)
out["descriptive: point-in-time top-6 (pack coins) sleeve"] = per(rcp)
if out["chosen"].startswith("A"):
    bh.to_frame("basket").to_parquet(ROOT / "results/gen397_basket_hourly.parquet")
(ROOT / "results/gen397.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

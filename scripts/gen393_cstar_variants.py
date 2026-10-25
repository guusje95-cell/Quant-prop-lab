"""Gen393 (config/gen393_protocol.json). Writes results/gen393.json.   cd scripts && python gen393_cstar_variants.py <v86 dump>"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
DUMP = sys.argv[1]; ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
g = {"__file__": str(ROOT / "scripts/gen373_honest_cstar.py")}
s = open(ROOT / "scripts/gen373_honest_cstar.py").read().split("\nout = {")[0].replace("DUMP = sys.argv[1]; sys.argv = sys.argv[:1]", f"DUMP = {DUMP!r}")
exec(compile(s, "g373", "exec"), g)
own_size, hourly, Dc, cand = g["own_size"], g["hourly"], g["Dc"], g["cand"]
import crypto_sleeves as CS
END = "2026-09-30"
dd = lambda h: h.groupby(h.index.floor("D")).sum()
shp = lambda h, a="2022", z=END: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
base = pd.read_parquet(ROOT / "results/k1_sleeves.parquet")
s3 = open(ROOT / "scripts/gen383_ensembles.py").read().split("T = {")[0]; g3 = {"__file__": str(ROOT / "scripts/gen383_ensembles.py")}; exec(compile(s3, "g383", "exec"), g3)
b391 = pd.read_parquet(ROOT / "results/gen391_basket_hourly.parquet")["basket"].reindex(base.index).fillna(0.0)
V93 = base.assign(**{"trend 4h": g3["te"], "alt kimchi": g3["ke"], "diversifier basket": b391})
v93 = unit(CS.portfolio_v5(V93)[0]); REF = (shp(v93), per(v93))
def fixed(coins):
    m = pd.DataFrame(False, index=Dc.index, columns=cand); m[list(coins)] = True
    return hourly(own_size(m, len(coins))).reindex(base.index).fillna(0.0)
T = {"A no C*": V93.drop(columns="C*"), "B C* BTC/ETH": V93.assign(**{"C*": fixed(("BTC", "ETH"))}), "C C* BTC/ETH/SOL": V93.assign(**{"C*": fixed(("BTC", "ETH", "SOL"))})}
out = {"reference v9.3": [REF[0], REF[1]], "trials": {}}
for k, H in T.items():
    b = unit(CS.portfolio_v5(H)[0]); out["trials"][k] = {"2022-24": shp(b, "2022", "2024"), "book": [shp(b), per(b)], "C* sleeve": per(H["C*"]) if "C*" in H else None}
ch = max(out["trials"], key=lambda k: out["trials"][k]["2022-24"]); r = out["trials"][ch]["book"]
out["chosen"] = ch; out["pass"] = bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))
(ROOT / "results/gen393.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

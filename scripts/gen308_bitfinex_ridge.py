"""Gen308 (config/gen308_protocol.json): Bitfinex margin features in the v8.4 / bf2.3 ridges. Writes results/gen308.json."""
import json
import numpy as np
import pandas as pd
import ridge_live as RL
import v7lab as L
import bf2lab as F
END = L.END
_src = open(L.ROOT / "scripts/gen304_ridge_feats2.py").read()
_g = {}; exec(_src[:_src.index("us = IS.hourly")], _g)    # walk() and per_coin() from Gen304, unchanged
walk, per_coin = _g["walk"], _g["per_coin"]


def bfx(c):
    lo = pd.read_parquet(L.ROOT / f"research_data/bitfinex/t{c}USD_long_1h.parquet")["size"]
    sh = pd.read_parquet(L.ROOT / f"research_data/bitfinex/t{c}USD_short_1h.parquet")["size"]
    lo, sh = lo[lo.index.hour == 23], sh[sh.index.hour == 23]; lo.index = lo.index.floor("D"); sh.index = sh.index.floor("D")
    f = pd.DataFrame({"bls": np.log(lo / sh.where(sh > 0)), "dlong7": np.log(lo).diff(7), "dshort7": np.log(sh.where(sh > 0)).diff(7)})
    return f.loc[:END]


out = {"reference v8.4": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2.3": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
DV = RL.predictions(END, spot=True, kb=True, volscale=True, vrp=True, cal=True).drop(columns=["y"])
DB = RL.predictions(END, spot=True, vrp=True, cal=True).drop(columns=["y"])
L.judge("bitfinex margin v8.4", L.perp(walk(per_coin(DV, bfx), True)), out, dev_start="2021-01-01", replace_ridge=True)
F.judge("bitfinex margin bf2.3", F.cfd(walk(per_coin(DB, bfx), False)), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(L.ROOT / "results/gen308.json", "w"), indent=1)

"""Gen309 / Gen309b: Deribit options skew, put/call ratio and taker call flow as ridge features. QPL_REF / QPL_BF_REF pick the books
(Gen309: v8.4 / bf2.3; Gen309b: v8.6 / bf2.6). Writes results/<gen>.json (GEN env, default gen309)."""
import json
import os
import numpy as np
import pandas as pd
import ridge_live as RL
import v7lab as L
import bf2lab as F
END = L.END; GEN = os.environ.get("GEN", "gen309"); STRICT = GEN == "gen309b"
_src = open(L.ROOT / "scripts/gen304_ridge_feats2.py").read(); _g = {}; exec(_src[:_src.index("us = IS.hourly")], _g)
walk, per_coin = _g["walk"], _g["per_coin"]
OPT = L.ROOT / "research_data/deribit_options"


def opt(c):
    d = pd.read_parquet(OPT / f"{c}_options_daily.parquet"); d["day"] = pd.to_datetime(d["day"])
    g = lambda m: d[m].groupby("day")
    iv = lambda m: g(m)["iv_sum"].sum() / g(m)["amount"].sum()
    put = (d.type == "P") & (d.mny == "0.85-0.95") & (d.ten == "8-45d"); call = (d.type == "C") & (d.mny == "1.05-1.15") & (d.ten == "8-45d")
    days = pd.date_range("2020-01-01", END)
    f = pd.DataFrame({"skew": (iv(put) - iv(call)).reindex(days)})
    pa = g(d.type == "P")["amount"].sum().reindex(days); ca = g(d.type == "C")["amount"].sum().reindex(days)
    f["skew7"] = f["skew"].diff(7); f["pcr"] = np.log(pa / ca); f["pcr7"] = f["pcr"].diff(7)
    cb = g((d.type == "C") & (d.side == "buy"))["amount"].sum().reindex(days).fillna(0); cs = g((d.type == "C") & (d.side == "sell"))["amount"].sum().reindex(days).fillna(0)
    f["callflow"] = ((cb - cs) / (cb + cs)).replace([np.inf, -np.inf], np.nan)
    return f


out = {"books": [os.environ.get("QPL_REF", "v8.6"), os.environ.get("QPL_BF_REF", "bf2.6")],
       "reference v": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
cov = opt("BTC"); out["feature coverage (share of days with skew)"] = round(float(cov["skew"].loc["2021":].notna().mean()), 3)
DV = RL.predictions(END, spot=True, kb=True, volscale=True, vrp=True, cal=True).drop(columns=["y"])
DB = RL.predictions(END, spot=True, vrp=True, cal=True).drop(columns=["y"])
out["check v ridge"] = float((L.perp(walk(DV, True)) - L.RIDGE).abs().max()); out["check bf ridge"] = float((F.cfd(walk(DB, False)) - F.HB_RIDGE).abs().max())


def judge_strict(B1, k, R):
    return bool(B1 >= R[0] + 0.05 and k[0] >= R[1][0] and k[1] >= R[1][1] and k[2] >= R[1][2])


rv = L.judge("options features (v)", L.perp(walk(per_coin(DV, opt), True)), out, dev_start="2021-01-01", replace_ridge=True)
rb = F.judge("options features (bf)", F.cfd(walk(per_coin(DB, opt), False)), out, dev_start="2021-01-01", replace_ridge=True)
if STRICT:
    out["v pass (strict)"] = judge_strict(rv["v7"][0], rv["v7"][1], L.REF); out["bf pass (strict)"] = judge_strict(rb["bf2"][0], rb["bf2"][1], F.REF)
print(out); json.dump(out, open(L.ROOT / f"results/{GEN}.json", "w"), indent=1)

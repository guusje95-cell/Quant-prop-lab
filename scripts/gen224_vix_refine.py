"""Gen224 (config/gen224_protocol.json): VIX-implied F5, VIX spike reversal, VIX-scaled R1. Writes results/gen224.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], c)
F, S, TUNE, JUDGE, IX, D, daily_book = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "IX", "D", "daily_book"))
import fbook as B
M2 = ROOT / "research_data/more2"
vix = pd.read_parquet(M2 / "vix_VIX.parquet")["close"].reindex(IX).ffill(); vxn = pd.read_parquet(M2 / "vix_VXN.parquet")["close"].reindex(IX).ffill()
E = ["ES", "NQ"]; RE = pd.DataFrame({r: D[r].r for r in E}).reindex(IX)
rep, changes = {}, {}


def svt(p, fit_end="2022-12-31"):
    sd = p.rolling(60, min_periods=40).std().shift(1); return p * (p.loc[:fit_end].std() / sd).clip(upper=2).fillna(1.0)


# F5 current vs implied
rv = RE.rolling(20).std() * np.sqrt(252)
f5c = daily_book((0.5 * (0.15 / rv).clip(upper=2)).shift(1).fillna(0.0), E)
iv = pd.DataFrame({"ES": vix / 100, "NQ": vxn.fillna(vix * 1.2) / 100})
f5i = daily_book((0.5 * (0.15 / iv).clip(upper=2)).shift(1).fillna(0.0), E)
t = {"current": round(S(f5c, TUNE), 3), "implied": round(S(f5i, TUNE), 3)}; rep["F5i"] = t
if t["implied"] > t["current"]:
    changes["F5"] = svt(f5i)
# VIX spike reversal
spike = vix > 1.25 * vix.rolling(20).mean()
trig = (spike.shift(1).fillna(False)) & (vix < vix.shift(1))
res = []
for H in (5, 10):
    pos = trig.astype(float).shift(1).rolling(H, min_periods=1).max().fillna(0.0)           # from the next session for H days
    p = daily_book(pd.DataFrame({r: 0.5 * pos for r in E}), E); res.append((S(p, TUNE), H, p))
res.sort(key=lambda x: -x[0]); s, H, p = res[0]; ap = B.appraisal(p)
rep["VSR"] = {"tune": {f"H{x[1]}": round(x[0], 3) for x in res}, "chosen H": H, "appraisal": round(ap, 3), "time invested": round(float((p != 0).mean()), 3),
              "enters": bool(s > 0.3 and ap > 0.3)}
if rep["VSR"]["enters"]:
    changes["VSR"] = p
# R1 x VIX
r1 = {"__file__": str(ROOT / "scripts/gen155_r1_refine.py")}; exec(open(ROOT / "scripts/gen155_r1_refine.py").read().split("if __name__")[0], r1)
src = open(ROOT / "scripts/gen155_r1_refine.py").read().split("if __name__")[0]
src = src.replace("        w = (0.25 * sig * mult).fillna(0.0)", "        vm = (VIXS / VIXS.rolling(252, min_periods=120).median()).clip(0.5, 2).shift(1).reindex(c.index).ffill()\n        w = (0.25 * sig * mult * vm).fillna(0.0)")
r1v = {"__file__": str(ROOT / "scripts/gen155_r1_refine.py"), "VIXS": pd.read_parquet(M2 / "vix_VIX.parquet")["close"]}; exec(src, r1v)
pc, pv = r1["r1v"](4, "lowvol", 24), r1v["r1v"](4, "lowvol", 24)
t = {"current": round(S(pc, TUNE), 3), "vix-scaled": round(S(pv, TUNE), 3), "current check": round(S(B.sleeves()["R1"], TUNE), 3)}; rep["R1v"] = t
if t["vix-scaled"] > t["current"]:
    changes["R1"] = pv
out = {"families": rep, "changes": list(changes)}
if changes:
    out.update(B.judge(changes, "gen224"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen224.json", "w"), indent=1)

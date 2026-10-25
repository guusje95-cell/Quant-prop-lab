"""Gen400 (config/gen400_protocol.json). Writes results/gen400.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen396_relcrowd.py").read().split("\nC3 = (")[0]
g = {"__file__": str(ROOT / "scripts/gen396_relcrowd.py")}; exec(compile(src, "g396", "exec"), g)
dd, shp, per, unit, END, CS, V, sleeve, B, pnl, days = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "sleeve", "B", "pnl", "days"))
import alt_kimchi as AK
import ridge_live as RL
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"); rc6 = sleeve(C6)
V4 = V.assign(**{"relative crowding 6": rc6}); v94 = unit(CS.portfolio_v5(V4)[0]); REF = (shp(v94), per(v94))
Za = AK.zscores(END + " 23:00")
def kz(c):                                               # same construction as alt_kimchi.zscores, for one coin
    end = pd.Timestamp(END + " 23:00"); last_full = (end + pd.Timedelta(hours=1)).floor("D") - pd.Timedelta(days=1)
    fx = RL.usdkrw(); up = RL.upbit(c); bn = B.k5(c).close.resample("1h").last()
    fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:last_full + pd.Timedelta(hours=23)]
    kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    return ((kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()).reindex(Za.index)
Zb = Za.assign(BTC=kz("BTC"), ETH=kz("ETH"))
out = {"reference v9.4": [REF[0], REF[1]], "coins": list(Za.columns), "trials": {}}
for nm, Z in (("K1 relative kimchi", Za), ("K2 relative kimchi incl. BTC/ETH", Zb)):
    Zd = Z.sub(Z.mean(axis=1), axis=0); w = (0.15 * Zd.clip(-2, 2) / 2).fillna(0.0)          # row d decided at the close of d
    s = pnl(w.reindex(days)).reindex(V.index).fillna(0.0)                                   # pnl() shifts by one day: held during d+1
    b = unit(CS.portfolio_v5(V4.assign(**{nm: s}))[0]); r = [shp(b), per(b)]
    out["trials"][nm] = {"sleeve": per(s), "corr v9.4": round(float(pd.concat([dd(s), dd(v94)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3), "book": r,
                         "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
    print(nm, out["trials"][nm], flush=True)
(ROOT / "results/gen400.json").write_text(json.dumps(out, indent=1))

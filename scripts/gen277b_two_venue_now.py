"""Gen277b (config/gen277b_protocol.json): the Gen277 two-venue alt-kimchi sleeve replacing alt kimchi in v8.6 and bf2.6. Writes results/gen277b.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import bf2lab as F
import cfd_book as CB
src = open(L.ROOT / "scripts/gen277_two_venue.py").read(); g = {"__file__": str(L.ROOT / "scripts/gen277_two_venue.py")}
exec(src[:src.index("bk = L.CS.portfolio_v5")], g); W = g["W"]
END = L.END
out = {"reference v8.6": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2.6": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
strict = lambda B1, k, R: bool(B1 >= R[0] + 0.05 and k[0] >= R[1][0] and k[1] >= R[1][1] and k[2] >= R[1][2])
others = [a for a in L.ALTK if a.name != "alt kimchi"]
b = L.CS.portfolio_v5(pd.concat([L.H6, L.RIDGE, L.perp(W).rename("alt kimchi")] + others, axis=1).fillna(0.0))[0]
B1, k = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01"); out["v8.6 with two-venue alt kimchi"] = [round(B1, 3), np.round(k, 3).tolist()]; out["v8.6 pass (strict)"] = strict(B1, k, L.REF)
spec = pd.read_csv(sorted((F.ROOT / "research_data/firm_specs").glob("BrightFunded*20261021*.csv"))[-1], encoding="latin1")
ac = [c for c in W.columns if c in CB.ALT_CFD]; w = W[ac]
cost = pd.Series({c: CB.ALT_SPREAD[c] + CB.COMM for c in ac}) / 1e4
r = F._B.panel("close", "1h", ac).loc[:END + " 23:00"].pct_change(fill_method=None).fillna(0.0)
held = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
h = ((held * r).sum(axis=1) - held.diff().abs().fillna(held.abs()).mul(cost, axis=1).sum(axis=1)).reindex(F.IDXbf).fillna(0.0).rename("alt kimchi")
b = F.CS.portfolio_v5(pd.concat([F.HB0, F.IS0, F.HB_RIDGE.rename("ridge ML"), h] + [a for a in F.ALTK_BF if a.name != "alt kimchi"], axis=1).fillna(0.0))[0]
B1, k = F.sh(b, "2022-01-01", END), F.per(b, "2022-01-01"); out["bf2.6 with two-venue alt kimchi"] = [round(B1, 3), np.round(k, 3).tolist()]; out["bf2.6 pass (strict)"] = strict(B1, k, F.REF)
print(out); json.dump(out, open(L.ROOT / "results/gen277b.json", "w"), indent=1)

"""Gen336b (flagged post hoc, config/gen335_protocol.json): premium carry 60 + trend 4h + alt kimchi neighbourhood ensembles
together in v8.6. Appends to results/gen336.json."""
import itertools
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
import alt_kimchi as AK
END = L.END
H = pd.concat([L.H6, L.RIDGE] + L.ALTK, axis=1).fillna(0.0)
pc60 = lambda lk, hd: CS.premium_carry_breadth(w=CS.premium_breadth_weights(look=lk, hold=hd, invvol=True, tranched=True)).loc[:END + " 23:00"]
E = {"premium carry 60": sum(pc60(a, b) for a, b in itertools.product((5, 7, 10), (5, 7, 10))) / 9,
     "trend 4h": sum(CS.trend4h(n_in=n, n_out=n // 2).loc[:END + " 23:00"] for n in (15, 20, 30)) / 3,
     "alt kimchi": sum(L.perp(AK.weights(END + " 23:00", th=t)) for t in (0.75, 1.0, 1.25)) / 3}
for k, s in E.items():
    H[k] = s.reindex(H.index).fillna(0.0)
b = CS.portfolio_v5(H)[0]; k = [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()
R = [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist()
res = {"v8.6 D/T/H": k, "strict pass": bool(all(a >= c for a, c in zip(k[1:], R[1:])) and k[0] >= R[0] + 0.05), "flag": "post hoc"}
print(res, flush=True)
d = json.load(open(L.ROOT / "results/gen336.json")); d["Gen336b three robust ensembles together (post hoc)"] = res
json.dump(d, open(L.ROOT / "results/gen336.json", "w"), indent=1)

"""Gen320 (config/gen320_protocol.json). Writes results/gen320.json."""
import json
import numpy as np
import pandas as pd
import bf2lab as F
import cfd_book as CB
import crypto_sleeves as CS
END = F.END
out = {"reference bf2.4": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
R, pos, _ = CB.positions()
w = CS.premium_breadth_weights(coins=CB.CFD, invvol=True).reindex(columns=CB.CFD).fillna(0.0)
h = CB.sleeve_pnl(CB.d2h(w, pos["C*"].index), R).reindex(F.IDXbf).fillna(0.0)
old = CB.sleeve_pnl(pos["premium carry"], R).reindex(F.IDXbf).fillna(0.0)
out["check old sleeve == HB0"] = float((old - F.HB0["premium carry"].reindex(F.IDXbf).fillna(0.0)).abs().max())
HB = F.HB0.copy(); HB["premium carry"] = h
b = F.CS.portfolio_v5(pd.concat([HB, F.IS0, F.HB_RIDGE.rename("ridge ML")] + F.ALTK_BF, axis=1).fillna(0.0))[0]
B1, k = F.sh(b, "2022-01-01", END), F.per(b, "2022-01-01")
out["sleeve D/T/H new / old"] = [np.round(F.per(h, "2020-01-01"), 3).tolist(), np.round(F.per(old, "2020-01-01"), 3).tolist()]
out["bf2.4 with invvol 11-coin carry"] = [round(B1, 3), np.round(k, 3).tolist()]
out["pass"] = bool(B1 > F.REF[0] and k[1] >= F.REF[1][1] and k[2] >= F.REF[1][2])
print(out); json.dump(out, open(F.ROOT / "results/gen320.json", "w"), indent=1)

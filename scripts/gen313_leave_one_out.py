"""Gen313 (config/gen313_protocol.json): leave-one-sleeve-out for v8.4 and bf2.3. Writes results/gen313.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import bf2lab as F
END = L.END
out = {}
VH = pd.concat([L.H6, L.RIDGE] + L.ALTK, axis=1).fillna(0.0)
assert abs(L.sh(L.CS.portfolio_v5(VH)[0], "2022-01-01", END) - L.REF[0]) < 1e-9
for s in VH.columns:
    b = L.CS.portfolio_v5(VH.drop(columns=s))[0]; B1, k = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
    out["v8.4 without " + s] = {"book": [round(B1, 3), np.round(k, 3).tolist()], "pass": bool(B1 > L.REF[0] and k[1] >= L.REF[1][1] and k[2] >= L.REF[1][2])}
    print("v8.4 without", s, out["v8.4 without " + s], flush=True)
FH = pd.concat([F.HB0, F.IS0, F.HB_RIDGE.rename("ridge ML")] + F.ALTK_BF, axis=1).fillna(0.0)
assert abs(F.sh(F.CS.portfolio_v5(FH)[0], "2022-01-01", END) - F.REF[0]) < 1e-9
for s in FH.columns:
    b = F.CS.portfolio_v5(FH.drop(columns=s))[0]; B1, k = F.sh(b, "2022-01-01", END), F.per(b, "2022-01-01")
    out["bf2.3 without " + s] = {"book": [round(B1, 3), np.round(k, 3).tolist()], "pass": bool(B1 > F.REF[0] and k[1] >= F.REF[1][1] and k[2] >= F.REF[1][2])}
    print("bf2.3 without", s, out["bf2.3 without " + s], flush=True)
json.dump(out, open(L.ROOT / "results/gen313.json", "w"), indent=1)

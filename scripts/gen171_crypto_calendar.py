"""Gen171 (config/gen171_protocol.json): equity-flow calendar effects on BTC/ETH as a v7 sleeve. Writes results/gen171.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
c = {"__file__": str(ROOT / "scripts/gen161_vm_calendar.py")}; exec(open(ROOT / "scripts/gen161_vm_calendar.py").read().split("def sleeves(")[0], c)
M = c["M"]
gg = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}; exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], gg)
H6 = gg["H6"]
import crypto_sleeves as CS
P = pd.read_parquet(ROOT / "results/gen108_preds.parquet"); wml = P.pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
ml = CS._from_daily_weights(wml, ["BTC", "ETH"], 5).loc[:"2026-09-30 23:00"]
HV7 = pd.concat([H6, ml.rename("ridge ML")], axis=1).fillna(0.0)
sh = lambda x, a, b: (lambda d: float(d.mean() / d.std() * np.sqrt(365)))(x.loc[a:b].groupby(x.loc[a:b].index.floor("D")).sum())
per = lambda x, s: [sh(x, s, f"{int(s[:4]) + 2}-12-31" if s[:4] in ("2020",) else "2022-12-31"), sh(x, "2023-01-01", "2024-12-31"), sh(x, "2025-01-01", "2026-09-30")]
v7 = CS.portfolio_v5(HV7)[0]; B0 = sh(v7, "2022-01-01", "2026-09-30"); k0 = per(v7, "2022-01-01")
days = pd.date_range("2020-01-01", "2026-10-01")


def sleeve(mask):
    act = set(mask[mask > 0].index)
    w = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
    for d in days[1:]:
        if d in act:
            w.loc[d - pd.Timedelta(days=1)] = 0.5                     # decided at the close of d-1, held during d
    return CS._from_daily_weights(w, ["BTC", "ETH"], 7.5).loc[:"2026-09-30 23:00"]


V = {"CC1": M["FC"], "CC2": pd.concat(M.values(), axis=1).max(axis=1)}
out = {"v7": [round(B0, 3), np.round(k0, 3).tolist()]}
for n, m in V.items():
    sl = sleeve(m); p = per(sl, "2020-01-01")
    vb = CS.portfolio_v5(pd.concat([HV7, sl.rename("calendar")], axis=1).fillna(0.0))[0]; B1 = sh(vb, "2022-01-01", "2026-09-30"); k1 = per(vb, "2022-01-01")
    out[n] = {"sleeve D/T/H": np.round(p, 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()],
              "pass": bool(p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])}
    print(n, out[n], flush=True)
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen171.json", "w"), indent=1)

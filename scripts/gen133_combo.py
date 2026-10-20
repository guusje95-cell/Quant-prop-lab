"""Gen133 (config/gen133_protocol.json): v8 = v6 + ridge ML + premium-carry breadth; bf-b + ridge. Writes results/gen133.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}
exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], g)
CS, H6, per, sh = (g[k] for k in ("CS", "H6", "per", "sh"))
END = "2026-09-30"
P = pd.read_parquet(ROOT / "results/gen108_preds.parquet")
wml = P.pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
ml = CS._from_daily_weights(wml, ["BTC", "ETH"], 5).loc[:END + " 23:00"]
pb = CS.premium_carry_breadth()


def stats(H):
    b = CS.portfolio_v5(H.fillna(0.0))[0]; return b, round(sh(b, "2022-01-01", "2026-09-30"), 3), np.round(per(b, "2022-01-01"), 3).tolist()


v6b, v6s, v6k = stats(H6)
H7 = pd.concat([H6, ml.rename("ridge ML")], axis=1); v7b, v7s, v7k = stats(H7)
H8 = H7.copy(); H8["premium carry"] = pb.reindex(H8.index).fillna(0.0); v8b, v8s, v8k = stats(H8)
strict = lambda s1, k1, s0, k0: bool(s1 > s0 and k1[1] >= k0[1] and k1[2] >= k0[2])
out = {"v6": [v6s, v6k], "v7 (v6+ridge)": [v7s, v7k], "v8 (v6+ridge+breadth)": [v8s, v8k],
       "E1 v8 vs v6 pass": strict(v8s, v8k, v6s, v6k), "E2 v8 vs v7 pass": strict(v8s, v8k, v7s, v7k)}
# E3 bf-b + ridge at CFD costs
h = {"__file__": str(ROOT / "scripts/gen121_bf_breadth.py")}
exec(open(ROOT / "scripts/gen121_bf_breadth.py").read().split("b2, H2 = book(pos1, 2.0)")[0], h)
U, IDX, book, CB, posU, pos1, b0 = (h[k] for k in ("U", "IDX", "book", "CB", "posU", "pos1", "b0"))
idx1 = IDX.append(pd.DatetimeIndex([IDX[-1] + pd.Timedelta(hours=1)]))
wml_d = wml.reindex(columns=U).fillna(0.0)
posml = wml_d.reindex(wml_d.index.append(pd.DatetimeIndex([wml_d.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(idx1.floor("D")).set_axis(idx1).fillna(0.0)
CB.SLEEVES = CB.SLEEVES + ["ridge ML"]; pos2 = dict(pos1); pos2["ridge ML"] = posml
posU2 = dict(posU); posU2["ridge ML"] = posml * 0
b_bf, _ = h["book"](posU2) if False else (b0, None)
b3, H3 = book(pos2)
k0 = per(b0, "2022-01-01"); k3 = per(b3, "2022-01-01")
s0 = round(sh(b0, "2022-01-01", "2026-09-30"), 3); s3 = round(sh(b3, "2022-01-01", "2026-09-30"), 3)
out.update({"bf": [s0, np.round(k0, 3).tolist()], "bf-b + ridge": [s3, np.round(k3, 3).tolist()], "E3 pass": strict(s3, k3, s0, k0)})
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen133.json", "w"), indent=1)
pd.DataFrame({"v8": v8b}).to_parquet(ROOT / "results/gen133_v8.parquet")

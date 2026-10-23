"""Gen348c (registered in config/gen348b_protocol.json follow-up): the premium-spike reversion (Gen348 A, as registered) as a 10th
sleeve in v8.6 under the strict rule, and v8.6 + sleeve correlation. Writes results/gen348c.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
g = {}; src = open(L.ROOT / "scripts/gen348_events.py").read(); exec(compile(src.split("\nvd = L.V7")[0], "gen348", "exec"), g)
h = g["pnl"](g["posA"]()).reindex(L.H6.index).fillna(0.0).rename("premium spike")
b = L.book([h]); k = [round(L.sh(b, "2022-01-01", L.END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()
R = [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist()
out = {"reference v8.6": R, "v8.6 + premium spike": k, "strict pass": bool(all(a >= q for a, q in zip(k[1:], R[1:])) and k[0] >= R[0] + 0.05)}
print(out); json.dump(out, open(L.ROOT / "results/gen348c.json", "w"), indent=1)
h.to_frame().to_parquet(L.ROOT / "results/gen348_premium_spike.parquet")

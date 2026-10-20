"""Gen132 (config/gen132_protocol.json): O1 order flow as a 7th bf sleeve. Writes results/gen132.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen131_papers2.py")}
exec(open(ROOT / "scripts/gen131_papers2.py").read().split('book("O1')[0], g)
ratio, listed = g["ratio"], g["listed"]; per, sh, CS, HC = (g["g"][k] for k in ("per", "sh", "CS", "HC"))
h = {"__file__": str(ROOT / "scripts/gen121_bf_breadth.py")}
exec(open(ROOT / "scripts/gen121_bf_breadth.py").read().split("idx1 = IDX.append")[0], h)
U, IDX, pos0, book, CB, pnl = (h[k] for k in ("U", "IDX", "pos0", "book", "CB", "pnl"))
DAYS = ratio.index; W = pd.DataFrame(np.nan, index=DAYS, columns=U)
for d in DAYS[DAYS.weekday == 6]:
    s = ratio.loc[d, [c for c in U if c in ratio]].where(listed.loc[d, [c for c in U if c in listed]]).dropna()
    if len(s) < 10:
        continue
    n = max(1, len(s) // 5); w = pd.Series(0.0, index=U)
    w[s.nlargest(n).index] = 1.0 / n; w[s.nsmallest(n).index] = -1.0 / n; W.loc[d] = w
W = W.ffill().fillna(0.0)
idx1 = IDX.append(pd.DatetimeIndex([IDX[-1] + pd.Timedelta(hours=1)]))
posflow = W.reindex(W.index.append(pd.DatetimeIndex([W.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(idx1.floor("D")).set_axis(idx1).fillna(0.0)
posU = {s: p.reindex(columns=U).fillna(0.0) for s, p in pos0.items()}
b0, H0 = book(posU)
CB.SLEEVES = CB.SLEEVES + ["order flow"]; pos1 = dict(posU); pos1["order flow"] = posflow
b1, H1 = book(pos1)
s1 = H1["order flow"]; k0, k1 = per(b0, "2022-01-01"), per(b1, "2022-01-01"); ks = per(s1, "2020-01-01")
out = {"sleeve D/T/H": np.round(ks, 3).tolist(), "bf before": round(sh(b0, "2022-01-01", "2026-09-30"), 3), "bf after": round(sh(b1, "2022-01-01", "2026-09-30"), 3),
       "bf D/T/H before": np.round(k0, 3).tolist(), "bf D/T/H after": np.round(k1, 3).tolist()}
out["pass"] = bool(ks[0] > 0 and ks[1] >= 0.5 and ks[2] >= 0.3 and out["bf after"] > out["bf before"] and k1[1] >= k0[1] and k1[2] >= k0[2])
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen132.json", "w"), indent=1)

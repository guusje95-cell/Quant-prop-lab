"""Gen229 (config/gen229_protocol.json): bid-to-cover surprise -> Treasury futures. Writes results/gen229.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen140_optimise.py").read().split("GRID = {")[0]
g = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}; exec(src, g)
F, S, TUNE, JUDGE, daily_book, a, RR, VR, MR = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "daily_book", "a", "RR", "VR", "MR"))
import fbook as B
a = a.copy(); a["btc"] = pd.to_numeric(a.bidToCoverRatio, errors="coerce"); a = a.dropna(subset=["btc"]).sort_values("date")
a["surp"] = a.groupby("root").btc.transform(lambda s: s - s.shift(1).rolling(8, min_periods=4).median())
ix = RR.index


def sleeve(H):
    W = pd.DataFrame(0.0, index=ix, columns=MR)
    for _, e in a.dropna(subset=["surp"]).iterrows():
        if e.date not in ix or e.surp == 0:
            continue
        i = ix.get_loc(e.date); s = 0.10 / VR[e.root].iloc[i] / 4
        if np.isfinite(s):
            W.loc[ix[i + 1:i + 1 + H], e.root] += np.sign(e.surp) * s
    return daily_book(W, MR)


res = []
for H in (3, 5):
    p = sleeve(H); res.append((S(p, TUNE), H, p)); print(H, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, H, p = res[0]
out = {"best H": H, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "auctions used": int(a.surp.notna().sum()), "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"AUS": p}, "gen229"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen229.json", "w"), indent=1)

"""Gen216 (config/gen216_protocol.json): TFF dealer positioning in ZN/ZB. Writes results/gen216.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen163_bigmove.py")}; exec(open(ROOT / "scripts/gen163_bigmove.py").read().split("\nFAM = {")[0], g)
F, S, TUNE, JUDGE, D, daily_book = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book"))
import fbook as B
c = {"__file__": str(ROOT / "scripts/gen119_cot.py")}; cs = open(ROOT / "scripts/gen119_cot.py").read(); exec(cs[:cs.index("def contrarian_book")], c)
tff = c["load"]("cot_tff.parquet", {k: v for k, v in c["TFF"].items() if k in ("ZN", "ZB")}, ["Dealer_Positions_Long_All", "Dealer_Positions_Short_All"])
M = ["ZN", "ZB"]; R = pd.DataFrame({r: D[r].r for r in M}).sort_index(); R = R[R.index.weekday < 5]; vol = (R.rolling(60, min_periods=40).std() * np.sqrt(252)).shift(1)


def sleeve(th):
    W = pd.DataFrame(0.0, index=R.index, columns=M)
    for r in M:
        x = tff[r]; z = c["zscore"]((x["Dealer_Positions_Long_All"] - x["Dealer_Positions_Short_All"]) / x["Open_Interest_All"], 156, 104)
        s = pd.Series(np.where(z > th, 1.0, np.where(z < -th, -1.0, 0.0)), index=z.index)
        W[r] = c["weekly_to_daily"](s, R.index).fillna(0.0) * 0.10 / vol[r] / 2
    return daily_book(W.shift(1).fillna(0.0).where(np.isfinite, 0.0), M)


res = []
for th in (0.5, 1.0):
    p = sleeve(th); res.append((S(p, TUNE), {"th": th}, p)); print(th, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
res.sort(key=lambda x: -x[0]); s, prm, p = res[0]
out = {"best": prm, "tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"DLR": p}, "gen216"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen216.json", "w"), indent=1)

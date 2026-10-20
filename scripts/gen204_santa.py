"""Gen204 (config/gen204_protocol.json): Santa Claus rally on ES/NQ. Writes results/gen204.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], c)
F, S, TUNE, JUDGE, IX, daily_book = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "IX", "daily_book"))
import fbook as B
m = pd.Series(0.0, index=IX)
for (y, mo), gg in IX.to_series().groupby([IX.year, IX.month]):
    if mo == 12:
        m.loc[gg.index[-5:]] = 1.0
    if mo == 1:
        m.loc[gg.index[:2]] = 1.0
p = daily_book(pd.DataFrame({r: m * 0.5 for r in ("ES", "NQ")}), ["ES", "NQ"])
s = S(p, TUNE); out = {"tune": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
if out["enters"]:
    out.update(B.judge({"SANTA": p}, "gen204"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen204.json", "w"), indent=1)

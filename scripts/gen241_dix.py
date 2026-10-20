"""Gen241 (config/gen241_protocol.json): DIX timing of ES/NQ. Needs research_data/more2/squeeze_dix.csv. Writes results/gen241.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
f = ROOT / "research_data/more2/squeeze_dix.csv"
if not f.exists():
    sys.exit("squeeze_dix.csv not downloaded yet (get_squeeze_dix.bat)")
c = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], c)
F, S, TUNE, JUDGE, IX, daily_book = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "IX", "daily_book"))
import fbook as B
g = pd.read_csv(f); g.columns = [x.strip().lower() for x in g.columns]; g["date"] = pd.to_datetime(g["date"]); g = g.set_index("date").sort_index()
dix = g["dix"].astype(float).reindex(IX).ffill()
hi = (dix > dix.rolling(252, min_periods=200).quantile(0.8)).astype(float).shift(1)
pos = hi.rolling(20, min_periods=1).max().fillna(0.0)
p = daily_book(pd.DataFrame({r: 0.5 * pos for r in ("ES", "NQ")}), ["ES", "NQ"])
out = {"tune": round(S(p, TUNE), 3), "appraisal": round(B.appraisal(p), 3), "2023-26": round(S(p, JUDGE), 3), "time invested": round(float((pos > 0).mean()), 2)}
out["enters"] = bool(out["tune"] > 0.3 and out["appraisal"] > 0.3)
if out["enters"]:
    out.update(B.judge({"DIX": p}, "gen241"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen241.json", "w"), indent=1)

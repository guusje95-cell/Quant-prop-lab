"""Gen475 (config/gen475_protocol.json): natural-gas injection-season short as a futures-book sleeve. Writes results/gen475.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import fbook
import futures_db as F
d = F.daily("NG"); vol = d.r.rolling(60, min_periods=40).std() * np.sqrt(252)
w = (-(0.10 / vol).clip(upper=3.0)).where(d.index.month.isin(range(4, 11)), 0.0).fillna(0.0).shift(1).fillna(0.0)
pnl = w * d.r - w.diff().abs().fillna(w.abs()) * d.cost
base = fbook.sleeves(); ref = [round(F.sharpe(fbook.build(base), *s), 3) for s in F.SPLITS]
tune = round(F.sharpe(pnl, "2010-06-01", "2022-12-31"), 3); app = round(fbook.appraisal(pnl), 3)
b = fbook.build(base.assign(NGS=pnl)); r = [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
out = {"sleeve 2010-17 / 2018-22 / 2023-26": list(F.splits(pnl)), "tune 2010-22": tune, "appraisal 2010-22": app,
       "by year": {str(y): round(F.sharpe(pnl, str(y), str(y)), 2) for y in range(2011, 2027)},
       "enters": bool(tune >= 0.3 and app > 0), "reference": ref, "book": r}
out["pass"] = bool(out["enters"] and r[2] >= ref[2] + 0.05 and r[0] >= ref[0] and r[1] >= ref[1])
(ROOT / "results/gen475.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

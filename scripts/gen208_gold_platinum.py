"""Gen208 (config/gen208_protocol.json): gold/platinum ratio -> ES/NQ timing. Needs research_data/databento/PL_1h.parquet. Writes results/gen208.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
if not (ROOT / "research_data/databento/PL_1h.parquet").exists():
    sys.exit("PL data not downloaded yet (get_futures_extra.bat)")
c = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], c)
F, S, TUNE, JUDGE, IX, daily_book, monthly = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "IX", "daily_book", "monthly"))
import fbook as B
gc, pl = F.daily("GC").close.reindex(IX).ffill(), F.daily("PL").close.reindex(IX).ffill()
ME = IX.to_series().groupby(IX.to_period("M")).max()
gp = np.log(gc / pl).reindex(ME.values); gp.index = ME.values
z = (gp - gp.rolling(60, min_periods=36).mean()) / gp.rolling(60, min_periods=36).std()
zd = z.reindex(IX).ffill()
V = {"BIN": monthly(zd, lambda v: 1.0 if v > 0 else 0.0), "SCL": monthly(zd, lambda v: float(np.clip(v, 0, 2) / 2))}
sl = {k: daily_book(pd.DataFrame({r: 0.5 * p for r in ("ES", "NQ")}), ["ES", "NQ"]) for k, p in V.items()}
t = {k: round(S(p, TUNE), 3) for k, p in sl.items()}; ch = max(t, key=t.get)
out = {"tune": t, "chosen": ch, "2023-26": round(S(sl[ch], JUDGE), 3), "enters": bool(t[ch] > 0.3)}
if out["enters"]:
    out.update(B.judge({"GP": sl[ch]}, "gen208"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen208.json", "w"), indent=1)

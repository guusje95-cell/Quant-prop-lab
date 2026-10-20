"""Gen208b (config/gen208b_protocol.json): gold/platinum ratio from Dukascopy spot -> ES/NQ timing. Writes results/gen208b.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
RAW = ROOT / "research_data/dukascopy_daily"
c = {"__file__": str(ROOT / "scripts/gen184_cross_pred.py")}; exec(open(ROOT / "scripts/gen184_cross_pred.py").read().split("\nFAM = {")[0], c)
F, S, TUNE, JUDGE, IX, daily_book, monthly = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "IX", "daily_book", "monthly"))
import fbook as B
xau = pd.read_parquet(RAW / "XAUUSD_D1_raw.parquet").close; xpt = pd.read_parquet(RAW / "XPTUSD_D1_raw.parquet").close
gp = np.log(xau / xpt).dropna(); gpm = gp.resample("ME").last()                      # calendar month-end value (last spot day of the month)
z = (gpm - gpm.rolling(60, min_periods=36).mean()) / gpm.rolling(60, min_periods=36).std()
ME = IX.to_series().groupby(IX.to_period("M")).max()
zd = pd.Series(z.reindex(pd.PeriodIndex(ME.index, freq="M").to_timestamp("M")).to_numpy(), index=ME.values).reindex(IX).ffill()
V = {"BIN": monthly(zd, lambda v: 1.0 if v > 0 else 0.0), "SCL": monthly(zd, lambda v: float(np.clip(v, 0, 2) / 2))}
sl = {k: daily_book(pd.DataFrame({r: 0.5 * p for r in ("ES", "NQ")}), ["ES", "NQ"]) for k, p in V.items()}
t = {k: round(S(p, TUNE), 3) for k, p in sl.items()}; ch = max(t, key=t.get)
out = {"spot history": [str(gp.index.min().date()), str(gp.index.max().date())], "tune": t, "chosen": ch, "2023-26": round(S(sl[ch], JUDGE), 3),
       "2010-17 / 2018-22": [round(F.sharpe(sl[ch], *F.SPLITS[0]), 3), round(F.sharpe(sl[ch], *F.SPLITS[1]), 3)], "enters": bool(t[ch] > 0.3)}
if out["enters"]:
    bh = daily_book(pd.DataFrame({r: pd.Series(0.5, index=IX) for r in ("ES", "NQ")}), ["ES", "NQ"]); out["buy-and-hold tune"] = round(S(bh, TUNE), 3)
    out["beats buy-and-hold (rule)"] = bool(t[ch] > out["buy-and-hold tune"])
if out["enters"] and out.get("beats buy-and-hold (rule)", False):
    out.update(B.judge({"GP": sl[ch]}, "gen208b"))
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen208b.json", "w"), indent=1)

"""Gen270 (config/gen270_protocol.json): altcoin kimchi in bf2 at measured BrightFunded costs. Writes results/gen270.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import cfd_book
spec = pd.read_csv(sorted((ROOT / "research_data/firm_specs").glob("BrightFunded*20261021*.csv"))[-1], encoding="latin1")
meas = {s.split("/")[0].replace("XDG", "DOGE"): float(v) for s, v in zip(spec["symbol"], spec["spread_bp_median"]) if "/USD" in s}
for c in cfd_book.SPREAD.index:
    cfd_book.SPREAD[c] = 0.5 * meas[c]
import bf2lab as F
import alt_kimchi as AK
from qpl.lab import binance_pack as B
END = F.END
w = AK.weights(END + " 23:00"); coins = [c for c in w.columns if meas.get(c, 1e9) <= 50]; w = w[coins]
cost = pd.Series({c: 0.5 * meas[c] + 1.2 for c in coins}) / 1e4
H = B.panel("close", "1h", coins).loc[:END + " 23:00"]; r = H.pct_change(fill_method=None).fillna(0.0)
held = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
h = ((held * r).sum(axis=1) - held.diff().abs().fillna(held.abs()).mul(cost, axis=1).sum(axis=1)).reindex(F.IDXbf).fillna(0.0)
out = {"reference bf2 at measured costs": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()], "coins": coins,
       "cost bp per side": {c: round(float(v) * 1e4, 2) for c, v in cost.items()}}
F.judge("alt kimchi at measured costs", h, out)
json.dump(out, open(ROOT / "results/gen270.json", "w"), indent=1)

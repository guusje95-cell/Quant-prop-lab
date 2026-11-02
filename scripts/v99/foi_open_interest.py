"""F-OI (research/v99/foi_protocol.json): ES / NQ open-interest-confirmed momentum as a futures-book entrant. Writes results/v99/foi_open_interest.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import fbook
import futures_db as F


def sleeve(root):
    s = pd.read_parquet(ROOT / "research_data/databento_extra/fut_stats_daily.parquet")
    s = s[s.symbol.str[:-2] == root]
    oi = s[s.stat_type == 9].groupby("date")["value"].sum().sort_index()
    d = F.daily(root); r = d["r"]; r.index = pd.DatetimeIndex(r.index)
    oi = oi.reindex(r.index).ffill(limit=3)
    R5 = (1 + r).rolling(5).apply(np.prod, raw=True) - 1; dOI = oi.pct_change(5, fill_method=None)
    sig = pd.Series(np.where((R5 > 0) & (dOI > 0), 1.0, np.where((R5 < 0) & (dOI > 0), -1.0, 0.0)), index=r.index)
    pos = sig.shift(1).fillna(0.0)
    cost = pos.diff().abs().fillna(pos.abs()) * F.cost_frac(root, float(d["close"].iloc[-1]))
    return pos * r - cost


def main():
    s = (sleeve("ES") + sleeve("NQ")) / 2; s = s[s.index.weekday < 5]
    sh = lambda x, a, z: round(float(x.loc[a:z].mean() / x.loc[a:z].std() * np.sqrt(252)), 3)
    per = lambda x: [sh(x, "2010", "2017"), sh(x, "2018", "2022"), sh(x, "2023", "2026-09-30")]
    S = fbook.sleeves(); b0 = fbook.build(S); S["F-OI"] = s.reindex(S.index).fillna(0.0); b1 = fbook.build(S)
    ref, r = per(b0), per(b1)
    out = {"sleeve 2010-17 / 2018-22 / 2023-26": per(s), "appraisal vs ES/NQ (2010-22)": round(float(fbook.appraisal(s)), 3) if hasattr(fbook, "appraisal") else None,
           "book without / with": [ref, r], "pass": bool(r[2] >= ref[2] + 0.05 and r[0] >= ref[0] and r[1] >= ref[1])}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/foi_open_interest.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

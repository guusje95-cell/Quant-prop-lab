"""Gen96 part A: point-in-time check. Signals computed with data cut at each cutoff must equal the full-data signals for every row
that was decidable before the cutoff. Writes results/gen96_pit.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; S = Path(sys.argv[1]); rows = []
for name in ("cstar", "bounce", "weiss"):
    full = pd.read_parquet(S / f"{name}_full.parquet")
    for f in sorted(S.glob(f"{name}_20*.parquet")):
        cut = pd.Timestamp(f.stem.split("_", 1)[1].replace("_", " ")[:10])
        cutw = pd.read_parquet(f)
        if name == "weiss":
            known = cutw.index[cutw.index <= cut - pd.Timedelta(hours=1)]
        else:
            known = cutw.index[cutw.index + pd.Timedelta(days=1) <= cut]
        a = cutw.reindex(known).fillna(0.0); b = full.reindex(index=known, columns=a.columns).fillna(0.0)
        diff = (a - b).abs()
        rows.append({"signal": name, "cutoff": str(cut.date()), "rows compared": len(known), "rows different": int((diff.max(axis=1) > 1e-9).sum()),
                     "max abs diff": float(diff.max().max()), "last 30 rows different": int((diff.tail(30).max(axis=1) > 1e-9).sum())})
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen96_pit.csv", index=False)

"""CN-5 (execution, 0 alpha trials, approximate): the CN-1 net-execution saving applied to the Propr / Hyperliquid version of the crypto
book (M1 series, results/v99/m1_series_hl.parquet). Propr charges 7.5 bp per side (vs the 5 bp in CN-1), so the saving is scaled by
7.5 / 5 and by the ratio of the HL book's daily vol to the v9.8 book's (same sleeve structure, fewer event coins). Approximation: the
event sleeves differ between the books, but the saving comes only from the 8 non-event sleeves. Writes results/v99/cn5_propr.json."""
import json
import runpy
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
g = runpy.run_path(str(ROOT / "scripts/v99/cn1_crypto_netting.py"), run_name="cn1")
saving, d, book = g["saving"], g["d"], g["book"]
hl = pd.read_parquet(ROOT / "results/v99/m1_series_hl.parquet")
sh = lambda s: float(s.mean() / s.std() * np.sqrt(365))
out = {}
for col in ("capped", "uncapped"):
    x = d(hl[col]).loc["2022-01-01":"2026-09-30"]; k = x.std() / d(book).std() * 7.5 / 5
    y = x + (saving * k).reindex(x.index).fillna(0.0)
    per = {p: [round(sh(x.loc[a:b]), 3), round(sh(y.loc[a:b]), 3)] for p, (a, b) in {"2022": ("2022", "2022"), "2023-24": ("2023", "2024"), "2025-26": ("2025", "2026-09-30")}.items()}
    out[col] = {"2022-26 research / net": [round(sh(x), 3), round(sh(y), 3)], "by period": per}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/cn5_propr.json").write_text(json.dumps(out, indent=1))

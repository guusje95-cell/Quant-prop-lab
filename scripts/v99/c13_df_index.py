"""C13 (research/v99/c13_protocol.json). Writes results/v99/c13_df_index.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c10b_true_cap as T
import c1_cfd_port as C
import c3_ensembles as E
import cfd_book as CB
import fbook
from qpl.live import cfd_extra as X

CB.measured_costs()
BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
R = CB.hourly_returns(idx[-1]).reindex(idx).fillna(0.0); S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
b27 = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
b28 = b27.assign(**{"trend 4h": E.trend(R, (15, 20, 30)), "alt kimchi": E.altk(R, (0.75, 1.0, 1.25))})
EQ = ["P1", "R1", "T1", "T2", "FC", "MM", "OIL", "K3"]
d = fbook.build(pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet")[EQ])
h = pd.Series(0.0, index=idx); t = d.index + pd.Timedelta(hours=21); keep = t.isin(idx); h.loc[t[keep]] = d.to_numpy()[keep]
ref = C.full(T.book(b28, 1.0, 4.0))
c13 = C.full(T.book(b28.drop(columns=["vol-managed indices"]).assign(**{"daily-flat index book": h}), 1.0, 4.0))
corr = round(float(pd.concat([C.dd(h), C.dd(b28["vol-managed indices"])], axis=1).loc["2022":"2026-09-30"].corr().iloc[0, 1]), 3)
out = {"bf2.8 (reference)": ref, "C13 bf2.8 with the daily-flat index book": c13, "sleeve (daily-flat index book)": C.full(h),
       "old index sleeve": C.full(b28["vol-managed indices"]), "corr new vs old index sleeve 2022-26": corr}
out["pass"] = bool(c13[0] >= ref[0] + 0.05 and all(c13[1][i] >= ref[1][i] for i in range(3)))
print(json.dumps(out, indent=1)); (ROOT / "results/v99/c13_df_index.json").write_text(json.dumps(out, indent=1))

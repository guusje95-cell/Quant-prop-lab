"""v9.9 C4 (descriptive, 0 trials, no selection): leave-one-out of every sleeve of the bf2.7 CFD candidate, and per-sleeve Sharpe and
correlation with the crypto v9.8 book. Writes results/v99/c4_loo.json."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c1_cfd_port as C
from qpl.live import cfd_extra as X


def main():
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    base = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    v98 = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet")["port"]
    corr = lambda a: round(float(pd.concat([C.dd(a), C.dd(v98)], axis=1).loc["2022":"2026-09-30"].corr().iloc[0, 1]), 3)
    ref = C.full(C.book(base)); out = {"bf2.7 candidate": ref, "sleeves": {}}
    for s in base.columns:
        r = C.full(C.book(base.drop(columns=s)))
        out["sleeves"][s] = {"alone": C.full(base[s]), "book without it": r, "marginal": round(ref[0] - r[0], 3), "corr with crypto v9.8": corr(base[s])}
        print(s, out["sleeves"][s], flush=True)
    (ROOT / "results/v99/c4_loo.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

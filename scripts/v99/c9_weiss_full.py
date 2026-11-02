"""C9 (research/v99/c9_protocol.json): Weiss expiry at full weight in the bf2.7 CFD book. Writes results/v99/c9_weiss_full.json."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c1_cfd_port as C
import crypto_sleeves as CS
from qpl.live import cfd_extra as X


def main():
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    base = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    ref = C.full(C.book(base)); orig = CS.v5_weights
    CS.v5_weights = lambda D, sleeves, weiss_scale=0.5: orig(D, sleeves, weiss_scale=1.0)
    try:
        r = C.full(C.book(base))
    finally:
        CS.v5_weights = orig
    out = {"bf2.7 (Weiss half)": ref, "Weiss full": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
    print(out); (ROOT / "results/v99/c9_weiss_full.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

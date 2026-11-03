"""R53 (research/v99/r53_protocol.json): ERC weights in the v9.9 candidate. Writes results/v99/r53_erc_v99.json."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c11_erc as E
import crypto_sleeves as CS
import r48_stress as S


def main():
    Ev = S.per_event(); idx = S.idx; H = S.V8.copy(); ex = {}
    for k, L in Ev.items():
        H[S.NAMES[k]] = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx)); ex[S.NAMES[k]] = sum((g for _, _, _, g in L), pd.Series(0.0, index=idx))
    base = S.capped(H, ex); orig = CS.v5_weights; CS.v5_weights = E.erc_weights
    try:
        r = S.capped(H, ex)
    finally:
        CS.v5_weights = orig
    out = {"v9.9 candidate (inverse-vol)": base, "v9.9 with ERC weights": r, "pass": bool(r[0] >= base[0] + 0.05 and all(r[1][i] >= base[1][i] for i in range(3)))}
    print(out); (ROOT / "results/v99/r53_erc_v99.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

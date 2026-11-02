"""R51 (research/v99/r51_protocol.json, FLAGGED): Weiss at full weight in the v9.9 candidate. Writes results/v99/r51_weiss_v99.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import r48_stress as S


def main():
    E = S.per_event(); idx = S.idx; H = S.V8.copy(); ex = {}
    for k, L in E.items():
        H[S.NAMES[k]] = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx)); ex[S.NAMES[k]] = sum((g for _, _, _, g in L), pd.Series(0.0, index=idx))
    base = S.capped(H, ex); orig = CS.v5_weights
    CS.v5_weights = lambda D, sleeves, weiss_scale=0.5: orig(D, sleeves, weiss_scale=1.0)
    try:
        ph, W, M = CS.portfolio_v5(H); k = S.kf(ph)
        _, wp = CS.weiss_expiry(positions=True); gu = wp.abs().sum(axis=1).reindex(idx).fillna(0.0)
        m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0); w = W["Weiss expiry"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
        g = gu * w * m * k * 1.5; f = (1.9 / g).clip(upper=1.0).fillna(1.0)
        H2 = H.assign(**{"Weiss expiry": H["Weiss expiry"] * f}); full = S.capped(H2, ex); unc = S.capped(H, ex)
        gmax = float(g.max())
    finally:
        CS.v5_weights = orig
    out = {"v9.9 candidate (Weiss half)": base, "Weiss full, uncapped": unc, "Weiss full, gross capped 1.9x": full, "Weiss gross max at full weight (x equity, risk 1.5)": round(gmax, 2),
           "pass": bool(full[0] >= base[0] + 0.05 and all(full[1][i] >= base[1][i] for i in range(3)))}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r51_weiss_v99.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

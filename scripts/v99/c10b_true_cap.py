"""C10b (correction, 0 trials): C9 / C10 capped the Weiss sleeve BEFORE the equal-risk weighting, which re-scales it back (R51 showed
capped == uncapped). Here the cap is applied AFTER weighting, on the Weiss contribution to the book (as the live bridge's 1:5 cap does):
book = sum_s w_s m k H_s, with the Weiss term multiplied by f = min(1, cap / Weiss gross). Writes results/v99/c10b_true_cap.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c1_cfd_port as C
import c3_ensembles as E
import c9b_checks as K
import cfd_book as CB
import crypto_sleeves as CS
from qpl.live import cfd_extra as X


def book(H, scale, cap):
    orig = CS.v5_weights; CS.v5_weights = lambda D, sleeves, weiss_scale=0.5: orig(D, sleeves, weiss_scale=scale)
    try:
        idx = H.index; ph, W, M = CS.portfolio_v5(H); k = 0.15 / (C.dd(ph.loc["2022":"2024"]).std() * np.sqrt(365))
        m = M.reindex(idx.floor("D")).set_axis(idx).ffill(); w = W["Weiss expiry"].reindex(idx.floor("D")).set_axis(idx).ffill()
        b = ph * k
        if cap:
            _, wp = CS.weiss_expiry(positions=True); gu = wp.abs().sum(axis=1).reindex(idx).fillna(0.0)
            g = (gu * w * m * k * 1.5).fillna(0.0); f = (cap / g).clip(upper=1.0).fillna(1.0)
            b = b - ((1 - f) * w * m * k * H["Weiss expiry"]).reindex(b.index).fillna(0.0)
        return b
    finally:
        CS.v5_weights = orig


def main():
    CB.measured_costs()
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    R = CB.hourly_returns(idx[-1]).reindex(idx).fillna(0.0); S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    b27 = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    b28 = b27.assign(**{"trend 4h": E.trend(R, (15, 20, 30)), "alt kimchi": E.altk(R, (0.75, 1.0, 1.25))})
    out = {"bf2.7 (Weiss half, no cap)": C.full(book(b27, 0.5, None)), "bf2.7 Weiss half, capped 4x": C.full(book(b27, 0.5, 4.0)),
           "bf2.7 + ensembles (Weiss half, capped 4x)": C.full(book(b28, 0.5, 4.0)),
           "C9 Weiss full, TRUE cap 4x": C.full(book(b27, 1.0, 4.0)), "C10 bf2.8 Weiss full + ensembles, TRUE cap 4x": C.full(book(b28, 1.0, 4.0)),
           "bf2.8 TRUE cap 5x (the firm's 1:5 limit)": C.full(book(b28, 1.0, 5.0)), "bf2.8 uncapped (not tradable)": C.full(book(b28, 1.0, None))}
    out["risk at 1.5, bf2.8 true cap 4x"] = K.stats(book(b28, 1.0, 4.0))
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/c10b_true_cap.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

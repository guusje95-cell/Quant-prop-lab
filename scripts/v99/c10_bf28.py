"""C10 (research/v99/c10_protocol.json, FLAGGED): bf2.8 = bf2.7 + Weiss full weight capped + Gen383 ensembles. Writes results/v99/c10_bf28.json."""
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


def capped_book(H, cap, scale=1.0):
    orig = CS.v5_weights; CS.v5_weights = lambda D, sleeves, weiss_scale=0.5: orig(D, sleeves, weiss_scale=scale)
    try:
        idx = H.index; ph, W, M = CS.portfolio_v5(H); k = 0.15 / (C.dd(ph.loc["2022":"2024"]).std() * np.sqrt(365))
        if cap:
            _, wp = CS.weiss_expiry(positions=True); gu = wp.abs().sum(axis=1).reindex(idx).fillna(0.0)
            m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0); w = W["Weiss expiry"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
            f = (cap / (gu * w * m * k * 1.5)).clip(upper=1.0).fillna(1.0); H = H.assign(**{"Weiss expiry": H["Weiss expiry"] * f})
            ph = CS.portfolio_v5(H)[0]
        return ph * k
    finally:
        CS.v5_weights = orig


def main():
    CB.measured_costs()
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    R = CB.hourly_returns(idx[-1]).reindex(idx).fillna(0.0)
    S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    b27 = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    b28 = b27.assign(**{"trend 4h": E.trend(R, (15, 20, 30)), "alt kimchi": E.altk(R, (0.75, 1.0, 1.25))})
    ref = C.full(capped_book(b27, None, 0.5)); r = C.full(capped_book(b28, 4.0, 1.0))
    out = {"bf2.7": ref, "bf2.8": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
    out["bf2.8 Weiss cap 3.5x / 4.5x"] = [C.full(capped_book(b28, 3.5, 1.0)), C.full(capped_book(b28, 4.5, 1.0))]
    X_cost2 = {k: v for k, v in S.items()}
    out["risk at 1.5: bf2.7 / bf2.8"] = [K.stats(capped_book(b27, None, 0.5)), K.stats(capped_book(b28, 4.0, 1.0))]
    pos = X.positions(pd.date_range("2021-01-01", idx[-1], freq="h"))
    import basket_live as BL
    from qpl.lab import binance_pack as B
    R6 = B.panel("close", "1h", list(BL.C6)).pct_change(fill_method=None).reindex(idx).fillna(0.0)
    c2 = X.costs(list(BL.C6)) * 2
    b28c = b28.assign(**{k: X.cfd_pnl(v.reindex(idx), R6, c2) for k, v in pos.items()})
    out["bf2.8 with 2x costs on the rc6 / basket CFD sleeves"] = C.full(capped_book(b28c, 4.0, 1.0))
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/c10_bf28.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

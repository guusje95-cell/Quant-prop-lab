"""C11 (research/v99/c11_protocol.json): equal-risk-contribution weights in bf2.8. Writes results/v99/c11_erc.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c1_cfd_port as C
import c10b_true_cap as T
import c3_ensembles as E
import cfd_book as CB
import crypto_sleeves as CS
from qpl.live import cfd_extra as X


def erc_weights(D, sleeves, weiss_scale=0.5, shrink=0.5):
    """Gen338 erc_weights, unchanged"""
    W = pd.DataFrame(np.nan, index=D.index, columns=list(sleeves))
    for m in D.index[~D.index.to_period("M").duplicated()]:
        hist = D.loc[m - pd.Timedelta(days=365):m - pd.Timedelta(days=1)]
        live = [c for c in sleeves if (hist[c] != 0).sum() >= (6 if c == "Weiss expiry" else 30) and hist[c].std() > 0]
        if len(live) < 2:
            continue
        S = hist[live].cov().to_numpy() * 365; S = (1 - shrink) * S + shrink * np.diag(np.diag(S))
        b = np.ones(len(live)); b[[i for i, c in enumerate(live) if c == "Weiss expiry"]] = weiss_scale; b = b / b.sum()
        x = b / np.sqrt(np.diag(S))
        for _ in range(500):
            rc = x * (S @ x) / (x @ S @ x); x = x * np.sqrt(b / np.maximum(rc, 1e-12)); x = x / x.sum()
        vol = np.sqrt(x @ S @ x); x = x * 0.10 / vol / len(live) * np.sqrt(len(live))
        W.loc[m, :] = 0.0; W.loc[m, live] = x
    return W.ffill().fillna(0.0)


def main():
    CB.measured_costs()
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    R = CB.hourly_returns(idx[-1]).reindex(idx).fillna(0.0); S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    b28 = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    b28 = b28.assign(**{"trend 4h": E.trend(R, (15, 20, 30)), "alt kimchi": E.altk(R, (0.75, 1.0, 1.25))})
    ref = C.full(T.book(b28, 1.0, 4.0)); orig = CS.v5_weights; CS.v5_weights = erc_weights
    try:
        r = C.full(T.book(b28, 1.0, 4.0))
    finally:
        CS.v5_weights = orig
    out = {"bf2.8 (inverse-vol, true cap)": ref, "bf2.8 with ERC weights": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
    print(out); (ROOT / "results/v99/c11_erc.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

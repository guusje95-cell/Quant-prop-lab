"""Equal-risk-contribution sleeve weights (Gen338 C code, unchanged): monthly, trailing 365 days, covariance shrunk to its diagonal,
equal risk budgets (Weiss expiry at weiss_scale), scaled like crypto_sleeves.v5_weights (the level multiplier sets the final vol).
Used by the R53 candidate v9.9e and the hub composite option weights='erc'."""
from __future__ import annotations

import numpy as np
import pandas as pd


def erc_weights(D: pd.DataFrame, sleeves, weiss_scale: float = 0.5, shrink: float = 0.5) -> pd.DataFrame:
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

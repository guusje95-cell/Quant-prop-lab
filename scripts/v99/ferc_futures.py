"""F-ERC (research/v99/ferc_protocol.json): ERC weights for the futures book. Writes results/v99/ferc_futures.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import fbook


def erc_month(hist, shrink=0.5):
    S = hist.cov().to_numpy() * 252; S = (1 - shrink) * S + shrink * np.diag(np.diag(S)); n = len(hist.columns)
    b = np.ones(n) / n; x = b / np.sqrt(np.diag(S))
    for _ in range(500):
        rc = x * (S @ x) / (x @ S @ x); x = x * np.sqrt(b / np.maximum(rc, 1e-12)); x = x / x.sum()
    return pd.Series(x, index=hist.columns)


def build(P):
    P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
    W = pd.DataFrame(np.nan, index=P.index, columns=P.columns)
    for m in P.index[~P.index.to_period("M").duplicated()]:
        hist = P.loc[:m].iloc[-253:-1]
        live = [c for c in P.columns if (hist[c] != 0).sum() >= 20 and hist[c].std() > 0]
        if len(live) < 2:
            continue
        W.loc[m, :] = 0.0; W.loc[m, live] = erc_month(hist[live]).to_numpy()
    W = W.ffill().fillna(0.0); raw = (P * W).sum(axis=1)
    lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
    return (raw * lvl).dropna()


def main():
    S = fbook.sleeves(); b0 = fbook.build(S); b1 = build(S)
    sh = lambda x, a, z: round(float(x.loc[a:z].mean() / x.loc[a:z].std() * np.sqrt(252)), 3)
    per = lambda x: [sh(x, "2010-07", "2017"), sh(x, "2018", "2022"), sh(x, "2023", "2026-09-30")]
    out = {"current static 1/sd": per(b0), "ERC point-in-time": per(b1)}
    out["pass"] = bool(out["ERC point-in-time"][2] >= out["current static 1/sd"][2] + 0.05 and out["ERC point-in-time"][1] >= out["current static 1/sd"][1])
    print(out); (ROOT / "results/v99/ferc_futures.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

"""F-PV5 (research/v99/fpv5_protocol.json): point-in-time equal-risk construction for the futures book. Writes results/v99/fpv5_futures.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import fbook


def pv5(P, target=0.10, cap=3.0):
    P = P[P.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
    W = pd.DataFrame(np.nan, index=P.index, columns=P.columns)
    for m in P.index[~P.index.to_period("M").duplicated()]:
        hist = P.loc[:m].iloc[-253:-1]
        live = [c for c in P.columns if (hist[c] != 0).sum() >= 20 and hist[c].std() > 0]
        if len(live) < 2:
            continue
        w = pd.Series(target / (hist[live].std().to_numpy() * np.sqrt(252)), index=live) / len(live)
        W.loc[m, :] = 0.0; W.loc[m, w.index] = w.to_numpy()
    W = W.ffill().fillna(0.0); raw = (P * W).sum(axis=1)
    lvl = (target / (raw.rolling(252, min_periods=60).std() * np.sqrt(252))).shift(1)
    x1 = raw * lvl; tgt = (target / (x1.rolling(30).std() * np.sqrt(252))).clip(upper=cap).shift(1)
    return (raw * lvl * tgt).dropna()


def main():
    S = fbook.sleeves(); b0 = fbook.build(S); b1 = pv5(S)
    sh = lambda x, a, z: round(float(x.loc[a:z].mean() / x.loc[a:z].std() * np.sqrt(252)), 3)
    per = lambda x: [sh(x, "2010", "2017"), sh(x, "2018", "2022"), sh(x, "2023", "2026-09-30")]
    out = {"current (static 1/sd fit 2010-22)": per(b0), "point-in-time equal risk (PV5)": per(b1)}
    out["pass"] = bool(out["point-in-time equal risk (PV5)"][2] >= out["current (static 1/sd fit 2010-22)"][2] + 0.05 and out["point-in-time equal risk (PV5)"][1] >= out["current (static 1/sd fit 2010-22)"][1])
    out["corr of daily returns"] = round(float(pd.concat([b0, b1], axis=1).dropna().corr().iloc[0, 1]), 3)
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/fpv5_futures.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

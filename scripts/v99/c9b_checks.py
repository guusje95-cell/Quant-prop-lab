"""C9b (descriptive, 0 trials): risk of Weiss at full weight in the bf2.7 CFD book: worst day, max drawdown, Weiss gross exposure vs
the 1:5 crypto leverage cap at risk 1.5, and the book with the Weiss gross capped. Writes results/v99/c9b_checks.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c1_cfd_port as C
import crypto_sleeves as CS
from qpl.live import cfd_extra as X


def stats(b, risk=1.5):
    d = C.dd(b.loc["2022":"2026-09-30"]) * risk; eq = (1 + d).cumprod()
    return {"worst day %": round(float(d.min() * 100), 2), "max DD %": round(float((eq / eq.cummax() - 1).min() * 100), 2), "days < -2.5%": int((d < -0.025).sum())}


def main():
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    base = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    orig = CS.v5_weights; out = {}
    _, wp = CS.weiss_expiry(positions=True); gross_unit = wp.abs().sum(axis=1).reindex(idx).fillna(0.0)
    for lab, sc in (("Weiss half (bf2.7)", 0.5), ("Weiss full (C9)", 1.0)):
        CS.v5_weights = lambda D, sleeves, weiss_scale=0.5, sc=sc: orig(D, sleeves, weiss_scale=sc)
        ph, W, M = CS.portfolio_v5(base); k = 0.15 / (C.dd(ph.loc["2022":"2024"]).std() * np.sqrt(365))
        m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0); w = W["Weiss expiry"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
        g = gross_unit * w * m * k * 1.5
        out[lab] = {"book": C.full(ph * k), **stats(ph * k), "Weiss gross x equity at risk 1.5: max / p99 of active hours": [round(float(g.max()), 2), round(float(g[g > 0].quantile(0.99)), 2) if (g > 0).any() else 0]}
        CS.v5_weights = orig
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/c9b_checks.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

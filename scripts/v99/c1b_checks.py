"""v9.9 C1b (descriptive robustness of C1 C, 0 trials): costs x2 / x3 and entry one hour late for the two ported CFD sleeves; gross
leverage of the combined CFD book. Writes results/v99/c1b_checks.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import basket_live as BL
import c1_cfd_port as C
from qpl.lab import binance_pack as B


def main():
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    honest = BH.drop(columns=["premium carry", "premium carry BF"])
    R = B.panel("close", "1h", C.C6).pct_change(fill_method=None).reindex(idx).fillna(0.0)
    rpos = BL.rc_positions(idx)
    _, W = BL.basket(idx); bw = sum(w.reindex(columns=C.C6).fillna(0.0) for w in W.values())
    days = bw.index.append(pd.DatetimeIndex([bw.index[-1] + pd.Timedelta(days=1)]))
    bpos = bw.reindex(days).shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)
    base = C.COST.copy(); out = {}
    for lab, k, lag in (("as tested", 1, 0), ("costs x2", 2, 0), ("costs x3", 3, 0), ("entry 1 h late", 1, 1)):
        C.COST = base * k
        rc = C.cfd_pnl(rpos.shift(lag).fillna(0.0), R); bk = C.cfd_pnl(bpos.shift(lag).fillna(0.0), R)
        out[lab] = C.full(C.book(honest.assign(**{"rc6 CFD": rc, "basket CFD": bk}))); print(lab, out[lab], flush=True)
    C.COST = base
    g = (rpos.abs().sum(axis=1) + bpos.abs().sum(axis=1)).loc["2022":]
    out["gross of the two new sleeves before book weights (x equity at sleeve level): median / p99"] = [round(float(g.median()), 3), round(float(g.quantile(0.99)), 3)]
    (ROOT / "results/v99/c1b_checks.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

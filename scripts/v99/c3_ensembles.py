"""v9.9 C3 (research/v99/c3_protocol.json): Gen383 trend 4h and alt kimchi ensembles in the bf2.7 CFD candidate.
Writes results/v99/c3_ensembles.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import alt_kimchi as AK
import c1_cfd_port as C
import cfd_book as CB
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
from qpl.live import cfd_extra as X


def altk(R, ths):
    ws = [AK.weights(th=t) for t in ths]; aw = sum(ws) / len(ws)
    ac = [c for c in aw.columns if c in CB.ALT_CFD]; aw = aw[ac]
    ar = B.panel("close", "1h", ac).pct_change(fill_method=None).reindex(R.index).fillna(0.0)
    ap = aw.reindex(aw.index.append(pd.DatetimeIndex([aw.index[-1] + pd.Timedelta(days=1)]))).shift(1)
    p_ = ap.reindex(R.index.floor("D")).set_axis(R.index).fillna(0.0)
    acost = pd.Series({c: CB.ALT_SPREAD[c] + CB.COMM for c in ac}) / 1e4
    return (p_ * ar).sum(axis=1) - p_.diff().abs().fillna(p_.abs()).mul(acost, axis=1).sum(axis=1)


def trend(R, ns):
    pos = sum(CS.trend4h(n_in=n, n_out=n // 2, positions=True)[1] for n in ns) / len(ns)
    return CB.sleeve_pnl(pos.reindex(columns=CB.CFD).fillna(0.0), R)


def main():
    CB.measured_costs()
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    R = CB.hourly_returns(idx[-1]).reindex(idx).fillna(0.0)
    t1, a1 = trend(R, (20,)), altk(R, (1.0,))
    rep = {"trend 4h max abs diff vs dump": float((t1 - BH["trend 4h"]).abs().loc["2021":].max()),
           "alt kimchi max abs diff vs dump": float((a1 - BH["alt kimchi"]).abs().loc["2021":].max())}
    print(rep, flush=True)
    honest = BH.drop(columns=["premium carry", "premium carry BF"])
    S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    base = honest.assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    ref = C.full(C.book(base)); te, ae = trend(R, (15, 20, 30)), altk(R, (0.75, 1.0, 1.25))
    out = {"reproduction": rep, "reference bf2.7 candidate": ref, "sleeves single / ensemble": {"trend 4h": [C.full(BH["trend 4h"]), C.full(te)], "alt kimchi": [C.full(BH["alt kimchi"]), C.full(ae)]},
           "trend ensemble only": C.full(C.book(base.assign(**{"trend 4h": te}))), "alt kimchi ensemble only": C.full(C.book(base.assign(**{"alt kimchi": ae})))}
    r = C.full(C.book(base.assign(**{"trend 4h": te, "alt kimchi": ae}))); out["both (the registered change)"] = r
    out["pass"] = bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/c3_ensembles.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

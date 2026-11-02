"""v9.9 C2 (research/v99/c2_protocol.json): P6 vol-managed long on six non-US index CFDs as a separate sleeve of the bf2.7 candidate.
Writes results/v99/c2_intl_indices.json."""
import glob
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c1_cfd_port as C
import index_sleeve as IS
from qpl.live import cfd_extra as X

SYMS = {"DE40": "GER30.cash", "UK100": "UK100.cash", "JP225": "JAP225.cash", "EU50": "EU50.cash", "FR40": "FRA40.cash", "AUS200": "ASX/AUD"}
spec = pd.read_csv(sorted(glob.glob(str(ROOT / "research_data/firm_specs/BrightFunded*20261021*.csv")))[-1], encoding="latin1")
SPR = dict(zip(spec["symbol"], spec["spread_bp_median"]))


def p6_intl(idx, k=1.0):
    pnl = pd.Series(0.0, index=idx)
    for s, bf in SYMS.items():
        x = IS.hourly(s); r = x.close.reindex(idx).ffill(limit=72).pct_change().fillna(0.0)
        dret = r.groupby(r.index.floor("D")).sum(); vol = dret.rolling(20).std() * np.sqrt(252)
        w = (0.5 * (0.15 / vol).clip(upper=2.0)).shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)
        cost = k * max(1e-4, 0.5 * SPR[bf] / 1e4)
        pnl = pnl + (w * r - w.diff().abs().fillna(0.0) * cost) / len(SYMS)
    return pnl


def main():
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    honest = BH.drop(columns=["premium carry", "premium carry BF"])
    S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    base = honest.assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    ref = C.full(C.book(base)); s = p6_intl(idx)
    r = C.full(C.book(base.assign(**{"vol-managed intl indices": s})))
    r2 = C.full(C.book(base.assign(**{"vol-managed intl indices": p6_intl(idx, 2.0)})))
    v98 = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet")["port"]
    corr = lambda a, b: round(float(pd.concat([C.dd(a), C.dd(b)], axis=1).loc["2022":"2026-09-30"].corr().iloc[0, 1]), 3)
    out = {"reference bf2.7 candidate": ref, "sleeve vol-managed intl indices": C.full(s), "book with it": r,
           "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))), "costs x2 (descriptive)": r2,
           "corr sleeve vs crypto v9.8": corr(s, v98), "corr sleeve vs US index sleeve": corr(s, BH["vol-managed indices"]),
           "corr book vs crypto v9.8: before / after": [corr(C.book(base), v98), corr(C.book(base.assign(**{"vol-managed intl indices": s})), v98)]}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/c2_intl_indices.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

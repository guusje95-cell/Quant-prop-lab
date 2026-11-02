"""v9.9 C5 (research/v99/c5_protocol.json): relative crowding (unchanged rule) on 12 altcoin CFDs as a separate bf2.7 sleeve.
Writes results/v99/c5_rc_alt.json."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import basket_live as BL
import c1_cfd_port as C
from qpl.lab import binance_pack as B
from qpl.live import cfd_extra as X
ALT = ("AAVE", "ADA", "AVAX", "BCH", "DOT", "ETC", "FIL", "LINK", "LTC", "NEAR", "UNI", "XLM")


def main():
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    base = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    ref = C.full(C.book(base))
    six = BL.C6; BL.C6 = ALT
    try:
        pos = BL.rc_positions(idx)
    finally:
        BL.C6 = six
    R = B.panel("close", "1h", list(ALT)).pct_change(fill_method=None).reindex(idx).fillna(0.0)
    s = X.cfd_pnl(pos, R, X.costs(ALT))
    r = C.full(C.book(base.assign(**{"rc alt CFD": s})))
    v98 = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet")["port"]
    corr = lambda a, b: round(float(pd.concat([C.dd(a), C.dd(b)], axis=1).loc["2022":"2026-09-30"].corr().iloc[0, 1]), 3)
    out = {"reference bf2.7 candidate": ref, "sleeve rc alt CFD": C.full(s), "book with it": r,
           "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))),
           "corr vs rc6 CFD": corr(s, base["rc6 CFD"]), "corr vs crypto v9.8": corr(s, v98),
           "gross median / p99": [round(float(pos.abs().sum(axis=1).loc["2022":].median()), 3), round(float(pos.abs().sum(axis=1).loc["2022":].quantile(0.99)), 3)]}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/c5_rc_alt.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

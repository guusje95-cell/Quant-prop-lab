"""v9.9 C7 (research/v99/c7_protocol.json, FLAGGED proxy): the futures book's six US equity-timing sleeves as one bf2.7 CFD sleeve.
Writes results/v99/c7_equity_calendar.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c1_cfd_port as C
from qpl.live import cfd_extra as X
MEM = ["T1", "T2", "FC", "MM", "K3", "OIL"]


def main():
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    base = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    ref = C.full(C.book(base))
    F = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")[MEM]; F = F[F.index.weekday < 5].fillna(0.0)
    w = 1 / F.loc["2010":"2022"].std(); w = w / w.sum(); d = (F * w).sum(axis=1)
    h = pd.Series(0.0, index=idx); t = (d.index + pd.Timedelta(hours=21)); keep = t.isin(idx)
    h.loc[t[keep]] = d.to_numpy()[keep]
    r = C.full(C.book(base.assign(**{"US equity calendar CFD": h})))
    v98 = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet")["port"]
    corr = lambda a, b: round(float(pd.concat([C.dd(a), C.dd(b)], axis=1).loc["2022":"2026-09-30"].corr().iloc[0, 1]), 3)
    out = {"weights": w.round(3).to_dict(), "reference bf2.7 candidate": ref, "sleeve": C.full(h), "book with it": r,
           "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))),
           "corr sleeve vs crypto v9.8": corr(h, v98), "corr sleeve vs US index sleeve": corr(h, base["vol-managed indices"]),
           "corr book vs crypto v9.8 before / after": [corr(C.book(base), v98), corr(C.book(base.assign(**{"US equity calendar CFD": h})), v98)]}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/c7_equity_calendar.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

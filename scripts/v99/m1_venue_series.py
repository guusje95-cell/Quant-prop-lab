"""v9.9 M1 step 1 (research/v99/m1_protocol.json): hourly book series of the v9.9 candidate per venue. Run once per venue (fresh
process: the venue filter is patched before the event modules load):  python scripts/v99/m1_venue_series.py bybit | hl
Writes results/v99/m1_series_<venue>.parquet (columns: capped, uncapped) and prints Sharpe by period."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
VENUE = sys.argv[1]
import event_live as EL
if VENUE == "hl":
    HL = json.loads((ROOT / "research_data/hyperliquid_listings/first_funding.json").read_text())
    def hl_launch():
        out = {}
        for k, v in HL.items():
            b = "1000" + k[1:] if k.startswith("k") and k[1:].isupper() else k
            t = pd.Timestamp(v["first_funding_utc"])
            t = pd.Timestamp("2020-01-01") if t <= pd.Timestamp("2023-05-13") else t              # launch batch: counterfactual from the start
            out[EL._norm(b)] = min(t, out.get(EL._norm(b), t))
        return out
    EL.firm_launch = hl_launch
import crypto_sleeves as CS
import r48_stress as S


def series(capped: bool) -> pd.Series:
    E = S.per_event(); idx = S.idx; H = S.V8.copy(); ex = {}
    for k, L in E.items():
        H[S.NAMES[k]] = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx)); ex[S.NAMES[k]] = sum((g for _, _, _, g in L), pd.Series(0.0, index=idx))
    ph, W, M = CS.portfolio_v5(H); k = S.kf(ph)
    if not capped:
        return ph * k
    m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    w = lambda c: W[c].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    g = S.pos8.abs().sum(axis=1).reindex(idx).fillna(0.0) * w("listing short") * m * k * S.RISK
    for c, gr in ex.items():
        g = g + gr * w(c) * m * k * S.RISK
    kk = (0.045 / g).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0); H2 = H.copy(); H2["listing short"] *= kk
    for c in ex:
        H2[c] = H2[c] * kk
    return CS.portfolio_v5(H2)[0] * k


def main():
    out = pd.DataFrame({"capped": series(True), "uncapped": series(False)})
    out.to_parquet(ROOT / f"results/v99/m1_series_{VENUE}.parquet")
    print(VENUE, {c: S.full(out[c]) for c in out}, {k: len(v) for k, v in S.SRC.items()}, flush=True)


if __name__ == "__main__":
    main()

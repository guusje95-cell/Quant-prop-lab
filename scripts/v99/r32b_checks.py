"""v9.9 R32b (diagnostics of R32 B, no selection): futures-delisting sleeve per year of events, exposure, the 4.5% total low-cap cap,
and on top of the R30 candidate (v9.8 + Coinbase sleeve). Writes results/v99/r32b_checks.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import r16_coinbase as R16
import r30b_checks as RB
import r32_binance_tag_sleeves as R32
RISK = 1.5


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, pos8, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum(); kf = lambda x: 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    full = lambda b: [shp(b, "2022", "2026-09-30"), per(b)]
    EV = R32.events()["futures delisting"]; hf, n = R32.sleeve(EV, 14, idx)
    hv, Pv = RB.venue(list(R16.events().items()), idx)
    yrs = pd.Series([t.year for _, t in EV]).value_counts().sort_index().to_dict()
    out = {"futures-delisting events by year (parsed)": {int(k): int(v) for k, v in yrs.items()}}
    def capped(H, extra_cols):
        ph, W, M = CS.portfolio_v5(H); k = kf(ph); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
        w = lambda c: W[c].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
        g = pos8.abs().sum(axis=1).reindex(idx).fillna(0.0) * w("listing short") * m * k * RISK
        for c, P in extra_cols.items():
            g = g + P * w(c) * m * k * RISK
        kk = (0.045 / g).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0)
        H2 = H.copy(); H2["listing short"] = H2["listing short"] * kk
        for c in extra_cols:
            H2[c] = H2[c] * kk
        return full(CS.portfolio_v5(H2)[0] * k), full(ph * k)
    gross_f = (hf != 0).astype(float) * 0.05                                  # approximate gross of the futures-delisting sleeve (one coin at a time typical)
    H1 = V8.assign(**{"futures-delisting short": hf}); H2 = V8.assign(**{"venue listing short": hv}); H3 = H2.assign(**{"futures-delisting short": hf})
    out["v9.8 + futures-delisting sleeve (uncapped / capped)"] = capped(H1, {"futures-delisting short": gross_f})[::-1]
    out["v9.8 + Coinbase sleeve (uncapped / capped)"] = capped(H2, {"venue listing short": Pv.abs().sum(axis=1)})[::-1]
    out["v9.8 + Coinbase + futures-delisting sleeves (uncapped / capped)"] = capped(H3, {"venue listing short": Pv.abs().sum(axis=1), "futures-delisting short": gross_f})[::-1]
    ph, W, M = CS.portfolio_v5(H1); k = kf(ph); wf = W["futures-delisting short"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    mm = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0); eff = gross_f * wf * mm * k * RISK
    out["futures-delisting effective short % of equity when active: median / max"] = [round(float(eff[eff > 0].median() * 100), 2), round(float(eff.max() * 100), 2)]
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r32b_checks.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

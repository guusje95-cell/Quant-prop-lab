"""v9.9 R34b (diagnostics of R34, no selection): perp age >= 30 days (no overlap with the 30-day listing short), and the full candidate
ALL (+ this sleeve) with and without the 4.5% total low-cap cap. Writes results/v99/r34b_checks.json."""
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
import r22_upbit_r16rules as R22
import r30b_checks as RB
import r32_binance_tag_sleeves as R32
import r34_binance_add as R34
RISK = 1.5
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
s8, pos8, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
dd = lambda x: x.groupby(x.index.floor("D")).sum(); kf = lambda x: 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(x, a, z):
    d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
full = lambda b: [shp(b, "2022", "2026-09-30"), [shp(b, "2022", "2022"), shp(b, "2023", "2024"), shp(b, "2025", "2026-09-30")]]
def capped(H, extra):
    ph, W, M = CS.portfolio_v5(H); k = kf(ph); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    w = lambda c: W[c].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    g = pos8.abs().sum(axis=1).reindex(idx).fillna(0.0) * w("listing short") * m * k * RISK
    for c, gr in extra.items():
        g = g + gr * w(c) * m * k * RISK
    kk = (0.045 / g).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0); H2 = H.copy(); H2["listing short"] *= kk
    for c in extra:
        H2[c] = H2[c] * kk
    return full(CS.portfolio_v5(H2)[0] * k), full(ph * k)
E = R34.events(); E30 = {c: t for c, t in E.items() if EL._closes(c)[0].index.min() <= t - pd.Timedelta(days=30)}
ha, Pa = RB.venue(list(E.items()), idx); h30, _ = RB.venue(list(E30.items()), idx)
hu, Pu = RB.venue(list(R16.events().items()) + list(R22.upbit_events().items()), idx)
hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx); gf = (hf != 0).astype(float) * 0.05
out = {"events": len(E), "events with perp >= 30 days": len(E30),
       "v9.8 + add sleeve (perp >= 30 days)": full(CS.portfolio_v5(V8.assign(**{"binance add short": h30}))[0] * kf(CS.portfolio_v5(V8.assign(**{"binance add short": h30}))[0])),
       "v9.8 capped": capped(V8, {})[0]}
Hall = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf})
Hall2 = Hall.assign(**{"binance add short": ha})
out["ALL (uncapped, capped)"] = list(capped(Hall, {"venue listing short": Pu.abs().sum(axis=1), "futures-delisting short": gf})[::-1])
out["ALL + add sleeve (uncapped, capped)"] = list(capped(Hall2, {"venue listing short": Pu.abs().sum(axis=1), "futures-delisting short": gf, "binance add short": Pa.abs().sum(axis=1)})[::-1])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/r34b_checks.json").write_text(json.dumps(out, indent=1))

"""v9.9 P6 (research/v99/p6_protocol.json, FLAGGED): book exposure cut below BTC's N-day average. Writes results/v99/p6_regime.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
s8, _, _ = EL.pnl(idx); b = CS.portfolio_v5(V7.assign(**{"listing short": s8}))[0]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a, z):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
res = lambda h: {"dev 2022-24": shp(h, "2022", "2024"), "holdout 2025-26": shp(h, "2025", "2026-09-30"), "full": shp(h, "2022", "2026-09-30")}
btc = B.k5("BTC").close.resample("1D").last()
out = {"v9.8": res(unit(b)), "variants": {}}
for n in (100, 200):
    below = (btc < btc.rolling(n).mean()).shift(1).fillna(False)
    for sc in (0.5, 0.75):
        k = below.map({True: sc, False: 1.0}).reindex(b.index.floor("D")).set_axis(b.index).fillna(1.0)
        out["variants"][f"MA{n} x{sc}"] = res(unit(b * k)); print(n, sc, out["variants"][f"MA{n} x{sc}"], flush=True)
best = max(out["variants"], key=lambda k: out["variants"][k]["dev 2022-24"]); c = out["variants"][best]; r = out["v9.8"]
out["chosen"] = best if c["dev 2022-24"] > r["dev 2022-24"] else "none"
out["adopt"] = bool(out["chosen"] != "none" and c["holdout 2025-26"] >= r["holdout 2025-26"] + 0.05 and c["full"] >= r["full"])
(ROOT / "results/v99/p6_regime.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in ("v9.8", "chosen", "adopt")}))

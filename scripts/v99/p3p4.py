"""v9.9 P3 (sleeve-level vol targeting, select 2022-24 / judge 2025-26) and P4 (fixed neighbourhood ensembles, FLAGGED).
Writes results/v99/p3p4.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
import alt_kimchi as AK
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a, z):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
def book(H):
    b = unit(CS.portfolio_v5(H)[0]); return {"dev 2022-24": shp(b, "2022", "2024"), "holdout 2025-26": shp(b, "2025", "2026-09-30"),
                                             "full": shp(b, "2022", "2026-09-30"), "periods": [shp(b, "2022", "2022"), shp(b, "2023", "2024"), shp(b, "2025", "2026-09-30")]}
ref = book(V8); out = {"reference v9.8": ref, "P3": {}, "P4": {}}


def svt(H, w):
    D = H.groupby(H.index.floor("D")).sum(); k = (D.rolling(365, min_periods=60).std() / D.rolling(w, min_periods=w // 2).std()).clip(0.5, 2.0).shift(1).fillna(1.0)
    return H * k.reindex(H.index.floor("D")).set_axis(H.index)


for w in (30, 60):
    out["P3"][f"window {w}"] = book(svt(V8, w)); print("P3", w, out["P3"][f"window {w}"], flush=True)
best = max(out["P3"], key=lambda k: out["P3"][k]["dev 2022-24"])
c = out["P3"][best]
out["P3"]["chosen"] = best if c["dev 2022-24"] > ref["dev 2022-24"] else "none"
out["P3"]["adopt"] = bool(out["P3"]["chosen"] != "none" and c["holdout 2025-26"] >= ref["holdout 2025-26"] + 0.05 and c["full"] >= ref["full"])
tr = sum(CS.trend4h(coins=cs, n_in=n, n_out=n // 2) for s in ((15, 20, 30), (10, 15, 20), (20, 30, 40), (10, 20, 40)) for n_set in [s]
         for cs in (("BTC", "ETH", "SOL"), ("BTC", "ETH", "SOL", "BNB", "XRP")) for n in n_set) / (8 * 3)
dl = sum(CS._from_daily_weights(w, list(w.columns), 5) for w in [CS.delev_bounce_weights(th=t, hold=h) for t in (0.08, 0.10, 0.12) for h in (1, 2, 3)]) / 9
ak = sum(CS._from_daily_weights(w, list(w.columns), 5) for w in [AK.weights("2026-09-30", th=t) for s in ((0.75, 1.0, 1.25), (0.5, 0.75, 1.0), (1.0, 1.25, 1.5), (0.5, 1.0, 1.5)) for t in s]) / 12
E = {"trend 4h": tr.reindex(idx).fillna(0.0), "delev bounce": dl.reindex(idx).fillna(0.0), "alt kimchi": ak.reindex(idx).fillna(0.0)}
for k, v in list(E.items()) + [("all three", None)]:
    H = V8.assign(**E) if v is None else V8.assign(**{k: v})
    r = book(H); r["pass (flagged)"] = bool(r["full"] >= ref["full"] + 0.05 and all(r["periods"][i] >= ref["periods"][i] for i in range(3)))
    out["P4"][k] = r; print("P4", k, r, flush=True)
(ROOT / "results/v99/p3p4.json").write_text(json.dumps(out, indent=1)); print(json.dumps({"P3": out["P3"]["chosen"], "P3 adopt": out["P3"]["adopt"], "P4": {k: v["pass (flagged)"] for k, v in out["P4"].items()}}))

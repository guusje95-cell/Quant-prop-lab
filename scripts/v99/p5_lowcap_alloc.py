"""v9.9 P5 (research/v99/p5_protocol.json): how to allocate the total low-cap budget among event-short positions.
Writes results/v99/p5_lowcap_alloc.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a, z):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
s, pos, _ = EL.pnl(idx); ph, W, M = CS.portfolio_v5(V7.assign(**{"listing short": s}))
w = W["listing short"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
budget = (0.045 / (w * m * 0.902 * 1.5)).replace([np.inf], np.nan).shift(1).fillna(np.inf)      # gross event-short units allowed per hour


def hook_for(mode):
    def hook(P, CF):
        P = P.copy(); A = P.to_numpy(); nz = A != 0
        age = np.zeros_like(A)                                      # hours since the start of the current position run, per column
        for j in range(A.shape[1]):
            run = 0
            for i in range(A.shape[0]):
                run = run + 1 if nz[i, j] else 0; age[i, j] = run
        B = budget.reindex(P.index).to_numpy()
        for i in np.where(nz.any(axis=1))[0]:
            g = np.abs(A[i]).sum(); b = B[i]
            if not np.isfinite(b) or g <= b:
                continue
            if mode == "pro rata":
                A[i] *= b / g; continue
            cols = np.where(nz[i])[0]; order = cols[np.argsort(age[i, cols] if mode == "newest first" else -age[i, cols], kind="stable")]
            left = b
            for j in order:
                a = abs(A[i, j]); keep = min(a, left); A[i, j] = np.sign(A[i, j]) * keep; left -= keep
        return pd.DataFrame(A, index=P.index, columns=P.columns)
    return hook


out = {}
for mode in ("pro rata", "newest first", "oldest first"):
    sx, _, _ = EL.pnl(idx, pre_cap=hook_for(mode)); b = unit(CS.portfolio_v5(V7.assign(**{"listing short": sx}))[0])
    out[mode] = {"dev 2022-24": shp(b, "2022", "2024"), "holdout 2025-26": shp(b, "2025", "2026-09-30"), "full": shp(b, "2022", "2026-09-30")}
    print(mode, out[mode], flush=True)
best = max(out, key=lambda k: (out[k]["dev 2022-24"], k == "pro rata")); r = out["pro rata"]; c = out[best]
res = {"variants": out, "chosen": best, "adopt": bool(best != "pro rata" and c["holdout 2025-26"] >= r["holdout 2025-26"] + 0.05 and c["full"] >= r["full"])}
(ROOT / "results/v99/p5_lowcap_alloc.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))

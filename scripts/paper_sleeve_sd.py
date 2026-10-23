"""Backtest daily sd of every sleeve at unit size (2023-01-01..2026-09-30) for the paper monitor's sleeve alert
(config/paper_monitor.json). Writes results/paper_sleeve_sd.json. Run once per book version."""
import json
import os
import pandas as pd
out = {}
import v7lab as L
H = pd.concat([L.H6, L.RIDGE] + L.ALTK, axis=1).fillna(0.0)
out["v86"] = {c: float(v) for c, v in H.groupby(H.index.floor("D")).sum().loc["2023-01-01":L.END].std().items()}
import bf2lab as F
G = pd.concat([F.HB0, F.IS0, F.HB_RIDGE.rename("ridge ML")] + F.ALTK_BF, axis=1).fillna(0.0)
out["bf26"] = {c: float(v) for c, v in G.groupby(G.index.floor("D")).sum().loc["2023-01-01":F.END].std().items()}
json.dump(out, open(L.ROOT / "results/paper_sleeve_sd.json", "w"), indent=1); print(out)

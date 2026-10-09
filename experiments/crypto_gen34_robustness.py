"""Gen34 descriptive robustness of the chosen two-speed policies (no re-selection)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "experiments/crypto_gen32_improve.py").read_text().split("rng = np.random.default_rng(32)")[0]
G = {"__name__": "g32", "__file__": str(ROOT / "experiments/crypto_gen32_improve.py")}
exec(compile(src, "g32", "exec"), G)
E, SK, T = G["E"], G["SK"], G["T"]; weights, engine_daily, SQ = G["weights"], G["engine_daily"], G["SQ"]
from qpl.prop_simulation import cft_daily as CFT  # noqa: E402

POL = {"1PHASE": ("MAJ10", 0.15, 0.06, 0.008), "2PHASE": ("LIQUID2", 0.20, 0.08, 0.009)}
D = SK.load("1d"); MAJ = D["close"].loc["2017-08-17":"2026-10-08"]; H, L = D["high"].reindex_like(MAJ), D["low"].reindex_like(MAJ)
COLS = {"LIQUID2": ["BTC", "ETH"], "MAJ10": list(MAJ.columns)}


def unit(name, cmult=1.0, fund=0.0, delay=0):
    c, h, l = MAJ[COLS[name]], H[COLS[name]], L[COLS[name]]
    w = weights(E.signals(c), c, h, l)
    base = engine_daily(w, c, h, l).loc["2018-01-01":]
    k = 1.0 / float(base["net"].loc["2018":"2022"].std() * SQ)        # same unit scaling as gen34 (unstressed)
    w2 = w.shift(delay).fillna(0) if delay else w
    d = engine_daily(w2, c, h, l, cmult).loc["2018-01-01":]
    if fund:
        d["net"] = d["net"] - (w2.shift(1).fillna(0).loc["2018-01-01":] * fund * 3 / 1e4).sum(axis=1)
    return d[["net", "worst", "best"]] * k, k


out = {"L_live": {}}
for nm in COLS:
    _, k = unit(nm); out["L_live"][nm] = k
idx = unit("LIQUID2")[0].index
rng = np.random.default_rng(341); bidx = T.stationary_bootstrap_indices(len(idx), 1000, 20.0, rng)[:, :730]
for prog, (sc, vc, vf, fee) in POL.items():
    res = {"L_challenge": round(vc * out["L_live"][sc], 4), "L_funded": round(vf * out["L_live"]["LIQUID2"], 4)}
    for tag, kw, fee_ in (("base", {}, fee), ("fee_1.5pct", {}, 0.015), ("costs2x_funding", {"cmult": 2.0, "fund": 1.0}, fee), ("delay_1d", {"delay": 1}, fee)):
        uc, _ = unit(sc, **kw); uf, _ = unit("LIQUID2", **kw)
        rc = tuple((uc * vc)[k].to_numpy() for k in ("net", "worst", "best")); rf = tuple((uf * vf)[k].to_numpy() for k in ("net", "worst", "best"))
        st = [i for i in range(0, len(idx), 5) if pd.Timestamp("2023-01-01") <= idx[i] <= pd.Timestamp("2024-10-08")]
        sa = [i for i in range(0, len(idx), 5) if idx[i] <= pd.Timestamp("2024-10-08")]
        res[tag] = {"TEST_starts": CFT.summarize_pipeline([CFT.pipeline(*rc, *rf, s, prog, fee_) for s in st]),
                    "ALL_starts": CFT.summarize_pipeline([CFT.pipeline(*rc, *rf, s, prog, fee_) for s in sa]),
                    "bootstrap": CFT.summarize_pipeline([CFT.pipeline(*(x[b] for x in rc), *(x[b] for x in rf), 0, prog, fee_) for b in bidx])}
        print(prog, tag, json.dumps(res[tag]), flush=True)
    out[prog] = res
(ROOT / "results/crypto_gen34_robustness.json").write_text(json.dumps(out, indent=1, default=float))
print("L", out["L_live"], {p: (out[p]["L_challenge"], out[p]["L_funded"]) for p in POL})

"""Gen46 (descriptive extension of gen34, user question 'why not 4x?'): two-speed CFT pipeline with much higher challenge
risk. Same frozen E2 (MAJ10 challenge, LIQUID2 funded), same pipeline simulator; v_c up to 0.60 (~4x the gen34 choice)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "experiments/crypto_gen34_twospeed.py").read_text().split("out = {")[0]
G = {"__name__": "g34", "__file__": str(ROOT / "experiments/crypto_gen34_twospeed.py")}
exec(compile(src, "g34", "exec"), G)
CFT, T, F, arrs, idx = G["CFT"], G["T"], G["F"], G["arrs"], G["idx"]
FEE = {"1PHASE": 0.008, "2PHASE": 0.009}
VF = {"1PHASE": 0.06, "2PHASE": 0.08}
out = {}
bidx = T.stationary_bootstrap_indices(len(idx), 1000, 20.0, np.random.default_rng(46))[:, :730]
for prog in FEE:
    for vc in (0.15, 0.20, 0.30, 0.45, 0.60):
        rc = arrs("MAJ10", vc); rf = arrs("LIQUID2", VF[prog])
        st = [i for i in range(0, len(idx), 5) if pd.Timestamp("2023-01-01") <= idx[i] <= pd.Timestamp("2024-10-08")]
        sa = [i for i in range(0, len(idx), 5) if idx[i] <= pd.Timestamp("2024-10-08")]
        att = [CFT.simulate_start(rc[0], s, prog, mode="optimistic", max_days=548, lo=rc[1], hi=rc[2]) for s in sa]
        sm = CFT.summarize(att)
        out[f"{prog}|{vc}"] = {"per_attempt": {k: sm[k] for k in ("P_pass", "P_fail_daily", "P_fail_max", "median_days_to_pass")},
                               "TEST_pipeline": CFT.summarize_pipeline([CFT.pipeline(*rc, *rf, s, prog, FEE[prog]) for s in st]),
                               "ALL_pipeline": CFT.summarize_pipeline([CFT.pipeline(*rc, *rf, s, prog, FEE[prog]) for s in sa]),
                               "bootstrap": CFT.summarize_pipeline([CFT.pipeline(*(x[b] for x in rc), *(x[b] for x in rf), 0, prog, FEE[prog]) for b in bidx])}
        o = out[f"{prog}|{vc}"]
        print(prog, vc, o["per_attempt"], "| 24m net TEST", o["TEST_pipeline"]["mean_net"], "ALL", o["ALL_pipeline"]["mean_net"], "BOOT", o["bootstrap"]["mean_net"],
              "| months to funded", o["ALL_pipeline"]["median_months_to_funded"], "attempts", o["ALL_pipeline"]["mean_attempts"], flush=True)
F.append({"kind": "dev_evaluation", "hypothesis_id": "GEN46_HIGHRISK_CHALLENGE", "protocol": "descriptive extension of config/crypto_gen34_protocol.json",
          "result": {k: {"TEST": v["TEST_pipeline"]["mean_net"], "BOOT": v["bootstrap"]["mean_net"]} for k, v in out.items()}})
(ROOT / "results/crypto_gen46_highrisk_challenge.json").write_text(json.dumps(out, indent=1, default=float))

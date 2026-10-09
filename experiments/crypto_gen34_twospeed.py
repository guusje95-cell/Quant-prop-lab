"""Gen34 (config/crypto_gen34_protocol.json): two-speed CFT pipeline on frozen E2 (challenge LIQUID2/MAJ10, funded LIQUID2)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "experiments/crypto_gen32_improve.py").read_text().split("rng = np.random.default_rng(32)")[0]
G = {"__name__": "g32", "__file__": str(ROOT / "experiments/crypto_gen32_improve.py")}
exec(compile(src, "g32", "exec"), G)
E, SK, F, T = G["E"], G["SK"], G["F"], G["T"]
weights, engine_daily, SQ = G["weights"], G["engine_daily"], G["SQ"]
from qpl.prop_simulation import cft_daily as CFT  # noqa: E402

PROTO = "config/crypto_gen34_protocol.json"
VC = (0.06, 0.08, 0.10, 0.12, 0.15, 0.20); VF = (0.04, 0.06, 0.08)
FEE = {"2PHASE": 0.009, "1PHASE": 0.008}
BASE = {"2PHASE": 0.08, "1PHASE": 0.06}              # gen31 single-speed choices

D = SK.load("1d"); MAJ = D["close"].loc["2017-08-17":"2026-10-08"]
H, L = D["high"].reindex_like(MAJ), D["low"].reindex_like(MAJ)
unit = {}
for name, cols in (("LIQUID2", ["BTC", "ETH"]), ("MAJ10", list(MAJ.columns))):
    c, h, l = MAJ[cols], H[cols], L[cols]
    d = engine_daily(weights(E.signals(c), c, h, l), c, h, l).loc["2018-01-01":]
    k = 1.0 / float(d["net"].loc["2018":"2022"].std() * SQ)          # unit = 100% annual vol on 2018-2022
    unit[name] = d[["net", "worst", "best"]] * k
idx = unit["LIQUID2"].index
assert (idx == unit["MAJ10"].index).all()


def arrs(name, v, trunc=None):
    d = unit[name] * v
    if trunc is not None:
        d = d.loc[:trunc]
    return d["net"].to_numpy(), d["worst"].to_numpy(), d["best"].to_numpy()


def run_policy(prog, sc, vc, vf, a, z, trunc=None, step=5):
    rc = arrs(sc, vc, trunc); rf = arrs("LIQUID2", vf, trunc)
    n = len(rc[0])
    starts = [i for i in range(0, n, step) if pd.Timestamp(a) <= idx[i] <= pd.Timestamp(z)]
    return CFT.summarize_pipeline([CFT.pipeline(*rc, *rf, s, prog, FEE[prog]) for s in starts])


out = {"grid": {}, "chosen": {}, "eval": {}}
for prog in FEE:
    for sc in ("LIQUID2", "MAJ10"):
        for vc in VC:
            for vf in VF:
                out["grid"][f"{prog}|{sc}|{vc}|{vf}"] = run_policy(prog, sc, vc, vf, "2018-01-01", "2020-12-31", trunc="2022-12-31")
    best = max([k for k in out["grid"] if k.startswith(prog)], key=lambda k: out["grid"][k]["mean_net"])
    _, sc, vc, vf = best.split("|"); vc, vf = float(vc), float(vf)
    out["chosen"][prog] = {"S_c": sc, "v_c": vc, "v_f": vf, "SEL": out["grid"][best]}
    print(prog, "chosen", best, out["grid"][best], flush=True)
# evaluation: chosen vs gen31 single-speed baseline
rng = np.random.default_rng(34)
bidx = T.stationary_bootstrap_indices(len(idx), 2000, 20.0, rng)[:, :730]
for prog, ch in out["chosen"].items():
    res = {}
    for tag, (sc, vc, vf) in (("two_speed", (ch["S_c"], ch["v_c"], ch["v_f"])), ("gen31_single", ("LIQUID2", BASE[prog], BASE[prog]))):
        hist = run_policy(prog, sc, vc, vf, "2023-01-01", "2024-10-08")
        hist_all = run_policy(prog, sc, vc, vf, "2018-01-01", "2024-10-08")
        rc = arrs(sc, vc); rf = arrs("LIQUID2", vf); sims = []
        for b in bidx:
            sims.append(CFT.pipeline(*(x[b] for x in rc), *(x[b] for x in rf), 0, prog, FEE[prog]))
        res[tag] = {"policy": [sc, vc, vf], "TEST_2023_2024_starts": hist, "ALL_2018_2024_starts": hist_all, "bootstrap": CFT.summarize_pipeline(sims)}
    t, b = res["two_speed"], res["gen31_single"]
    gate = bool(t["TEST_2023_2024_starts"]["mean_net"] > b["TEST_2023_2024_starts"]["mean_net"]
                and (t["TEST_2023_2024_starts"]["median_months_to_funded"] or 99) < (b["TEST_2023_2024_starts"]["median_months_to_funded"] or 99)
                and t["bootstrap"]["mean_net"] > b["bootstrap"]["mean_net"] and t["bootstrap"]["P_net_pos"] >= 0.70)
    res["BETTER"] = gate
    out["eval"][prog] = res
    F.append({"kind": "holdout_evaluation", "hypothesis_id": f"GEN34_TWOSPEED_{prog}", "protocol": PROTO,
              "result": {"policy": res["two_speed"]["policy"], "BETTER": gate,
                         "TEST_mean_net": t["TEST_2023_2024_starts"]["mean_net"], "boot_mean_net": t["bootstrap"]["mean_net"]}})
    print(prog, json.dumps(res, default=float), flush=True)
(ROOT / "results/crypto_gen34_twospeed.json").write_text(json.dumps(out, indent=1, default=float))

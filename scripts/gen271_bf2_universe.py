"""Gen271 (config/gen271_protocol.json): bf2 with cheap extra CFD coins. python scripts/gen271_bf2_universe.py A|B|ref"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
add = {"A": ["BNB"], "B": ["BNB", "UNI", "NEAR", "AAVE"], "ref": []}[sys.argv[1]]
import cfd_book as CB
spec = pd.read_csv(sorted((ROOT / "research_data/firm_specs").glob("BrightFunded*20261021*.csv"))[-1], encoding="latin1")
meas = {s.split("/")[0].replace("XDG", "DOGE"): float(v) for s, v in zip(spec["symbol"], spec["spread_bp_median"]) if "/USD" in s}
CB.CFD = CB.CFD + add; CB.CFD_BASE = CB.CFD_BASE + add
CB.SPREAD = pd.Series({c: 0.5 * meas[c] for c in CB.CFD})
import os
os.environ["QPL_COSTS"] = "fixed"                                  # bf2lab must not overwrite the spreads set here
import bf2lab as F
r = {"added": add, "bf2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
print(json.dumps(r), flush=True)
f = ROOT / "results/gen271.json"; o = json.load(open(f)) if f.exists() else {}; o[sys.argv[1]] = r; json.dump(o, open(f, "w"), indent=1)

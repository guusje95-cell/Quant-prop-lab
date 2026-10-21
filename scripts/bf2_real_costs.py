"""bf2 with the BrightFunded spreads measured on 2026-10-21 (MT5 export, median of 10 samples) instead of the assumed ones.
    python scripts/bf2_real_costs.py model|full|half      (full: whole spread per side, bf2's convention; half: half spread per side)
Descriptive cost check, not a selection trial. Prints bf2 2022-26 / 2022 / TEST / HOLD."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
mode = sys.argv[1]; excl = sys.argv[2:]                 # optional: coins not traded (spread above a cost cap)
import cfd_book
spec = pd.read_csv(sorted((ROOT / "research_data/firm_specs").glob("BrightFunded*20261021*.csv"))[-1], encoding="latin1")
meas = {s.split("/")[0].replace("XDG", "DOGE"): v for s, v in zip(spec["symbol"], spec["spread_bp_median"]) if "/USD" in s}
if mode != "model":
    k = 1.0 if mode == "full" else 0.5
    for c in cfd_book.SPREAD.index:
        cfd_book.SPREAD[c] = k * float(meas[c])
print(mode, {c: round(float(v), 2) for c, v in cfd_book.SPREAD.items()}, flush=True)
if excl:                                               # an untradeable coin: make its cost prohibitive -> remove from the universe
    import cfd_book as _CB
    _CB.CFD = [c for c in _CB.CFD if c not in excl]; _CB.SPREAD = _CB.SPREAD.drop(excl)
import bf2lab as F
print(mode, "bf2", round(F.REF[0], 3), np.round(F.REF[1], 3).tolist(), flush=True)

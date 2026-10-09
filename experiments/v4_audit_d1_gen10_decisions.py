"""Audit V4-D1: gen10 hypotheses C1-C4 were evaluated (results/v4_crypto_gen10.csv) but no decision was recorded. Record them now from the stored table."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.research import factory as F, registry as R
ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "results/v4_crypto_gen10.csv")
F.append({"kind": "audit", "id": "V4-D1", "note": "gen10 C1-C4 decisions were computed in the screen table but not recorded; recorded now from results/v4_crypto_gen10.csv without re-running"})
for hid, g in df.groupby("hid"):
    b = g.loc[g.tr_sh.idxmax()]
    if b.tr_sh < 0.5 or b.tr_resid < 0.3:
        v, why = "REJECT", f"TRAIN best net {b.tr_sh:.2f} resid {b.tr_resid:.2f} (gate 0.5 / 0.3)"
    else:
        v, why = "VALIDATION_CANDIDATE", (f"TRAIN best {b.tr_sh:.2f} (resid {b.tr_resid:.2f}), VAL {b.va_sh:.2f} (resid {b.va_resid:.2f}); "
                                          f"{(g.tr_sh > 0).mean():.0%} variants TRAIN-positive. Not advanced separately: SUBSUMED into the frozen CT1 ensemble")
    R.set_verdict(hid, v, why)
    F.append({"kind": "decision", "hypothesis_id": hid, "verdict": v, "reason": why, "evidence": {"source": "results/v4_crypto_gen10.csv", "audit": "V4-D1"}})
    print(hid, v, why)

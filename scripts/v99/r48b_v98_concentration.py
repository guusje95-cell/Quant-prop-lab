"""v9.9 R48b (POST HOC, flagged diagnostic, 0 trials): R48 S1 failed (dropping the best 10% of events in the four new sleeves removes the
whole gain). Context check: the same stress on v9.8's OWN event short (drop its best 5% / 10% event coins, ranked by the short's price
move over the held hours), capped book as in R45. Writes results/v99/r48b_v98_concentration.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import event_live as EL
import r48_stress as S

idx = S.idx; seen = {}


def record(P, CF):
    for c in P.columns:
        held = P.index[P[c] != 0]
        if len(held) and c in CF and CF[c][0] is not None:
            cl = CF[c][0]; a = cl.asof(held[0]); b = cl.asof(held[-1] + pd.Timedelta(hours=1))
            seen[c] = float(-(b / a - 1)) if a and np.isfinite(a) and np.isfinite(b) else 0.0
    return P


def main():
    EL.pnl(idx, pre_cap=record); r = pd.Series(seen).sort_values(ascending=False)
    out = {"v9.8 capped": S.capped(S.V8, {}), "event coins": len(r)}
    for q in (0.05, 0.10):
        drop = set(r.index[:max(1, int(round(q * len(r))))])
        s, pos, _ = EL.pnl(idx, pre_cap=lambda P, CF: P.assign(**{c: 0.0 for c in P.columns if c in drop}))
        V = S.V8.assign(**{"listing short": s}); S.pos8 = pos
        out[f"v9.8 without its best {int(q * 100)}% event coins (capped)"] = S.capped(V, {})
        print(out, flush=True)
    (ROOT / "results/v99/r48b_v98_concentration.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

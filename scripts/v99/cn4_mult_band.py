"""CN-4 (research/v99/cn4_protocol.json). Writes results/v99/cn4_mult_band.json."""
import json
import runpy
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
g = runpy.run_path(str(ROOT / "scripts/v99/cn2_cfd_netting.py"), run_name="cn2")
C, POS, R, cost, book, sep, turn, Wh, mh, coins = (g[k] for k in ("C", "POS", "R", "cost", "book", "sep", "turn", "Wh", "mh", "coins"))


def band_mult(m, b=0.10):
    d = m.groupby(m.index.floor("D")).first(); out = []; cur = np.nan
    for v in d.to_numpy():
        if not np.isfinite(cur) or (np.isfinite(v) and abs(v / cur - 1) > b):
            cur = v
        out.append(cur)
    s = pd.Series(out, index=d.index); return s.reindex(m.index.floor("D")).set_axis(m.index)


def run(mult, risk=1.75):
    net = sum(POS[n].reindex(columns=coins).fillna(0.0).mul(Wh[n] * mult, axis=0) for n in POS)
    N = net.to_numpy(); held = np.zeros_like(N); h = np.zeros(N.shape[1]); band = 0.005 / risk
    for t in range(N.shape[0]):
        mv = np.abs(N[t] - h) > band; h = np.where(mv, N[t], h); held[t] = h
    Hd = pd.DataFrame(held, index=net.index, columns=net.columns); Rr = R.reindex(columns=net.columns).fillna(0.0)
    hc = (turn(Hd) * cost.reindex(net.columns)).sum(axis=1)
    base_net = sum(POS[n].reindex(columns=coins).fillna(0.0).mul(Wh[n] * mh, axis=0) for n in POS)
    # book = research book (per-member costs, daily multiplier) + member costs back - held costs + (held - research net) x returns
    return book + sep - hc + ((Hd - base_net) * Rr).sum(axis=1), hc


ref, c0 = run(mh); mb = band_mult(mh); cand, c1 = run(mb)
out = {"CN-3 reproduced (risk 1.75)": C.full(ref), "with the 10% multiplier band": C.full(cand),
       "annual cost CN-3 / with band": [round(float(C.dd(c0).loc["2022":"2026-09-30"].mean() * 365), 4), round(float(C.dd(c1).loc["2022":"2026-09-30"].mean() * 365), 4)],
       "multiplier updates per year": round(float((mb.groupby(mb.index.floor("D")).first().diff() != 0).sum() / ((mb.index[-1] - mb.index[0]).days / 365)), 1)}
r0, r1 = out["CN-3 reproduced (risk 1.75)"], out["with the 10% multiplier band"]
out["pass"] = bool(r1[0] >= r0[0] + 0.05 and all(r1[1][i] >= r0[1][i] for i in range(3)))
print(json.dumps(out, indent=1)); (ROOT / "results/v99/cn4_mult_band.json").write_text(json.dumps(out, indent=1))

"""CN-3 (execution, 0 alpha trials): bf2.8 net execution WITH the MT5 bridge's existing no-trade band (Rules.band_usd = $1,000 on a
$200K account, i.e. 0.5% of equity per coin) at account risk 1.75 / 2.0: trade a coin only when |target - held| > band, then to the
target. Builds on CN-2 (same positions, costs, weights): book_band = book + (per-member cost - held cost) + (held - net) x returns.
Writes results/v99/cn3_cfd_band.json."""
import json
import runpy
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
g = runpy.run_path(str(ROOT / "scripts/v99/cn2_cfd_netting.py"), run_name="cn2")
C, net, R, cost, book, sep, netc, turn = (g[k] for k in ("C", "net", "R", "cost", "book", "sep", "netc", "turn"))
out = {"bf2.8 research (per-member costs)": C.full(book), "net execution (CN-2)": C.full(book + (sep - netc))}
N = net.to_numpy(); Rv = R.reindex(columns=net.columns).fillna(0.0).to_numpy(); cv = cost.reindex(net.columns).to_numpy()
for risk in (1.75, 2.0):
    band = 0.005 / risk
    held = np.zeros_like(N); h = np.zeros(N.shape[1])
    for t in range(N.shape[0]):
        move = np.abs(N[t] - h) > band
        h = np.where(move, N[t], h); held[t] = h
    Hd = pd.DataFrame(held, index=net.index, columns=net.columns)
    hc = (turn(Hd) * cost).sum(axis=1)
    track = ((Hd - net) * R.reindex(columns=net.columns).fillna(0.0)).sum(axis=1)
    out[f"net + $1,000 band, risk {risk}"] = C.full(book + (sep - hc) + track)
    out[f"annual cost with band, risk {risk}"] = round(float(C.dd(hc).loc["2022":"2026-09-30"].mean() * 365), 4)
out["annual cost per-member / net"] = [round(float(C.dd(sep).loc["2022":"2026-09-30"].mean() * 365), 4), round(float(C.dd(netc).loc["2022":"2026-09-30"].mean() * 365), 4)]
print(json.dumps(out, indent=1)); (ROOT / "results/v99/cn3_cfd_band.json").write_text(json.dumps(out, indent=1))

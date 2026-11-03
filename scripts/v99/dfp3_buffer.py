"""DF-P3 (research/v99/dfp3_protocol.json): buffer-scaled sizing at a Topstep-like firm. Writes results/v99/dfp3_buffer.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import fbook
EQ = ["P1", "R1", "T1", "T2", "FC", "MM", "OIL", "K3"]
b = fbook.build(pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet")[EQ]).loc["2023-01-01":"2026-09-30"]; b = b[b.index.weekday < 5]


def run(x, scaled, acct=50_000.0, days=504):
    net, d = 0.0, 0
    while d < days:
        bal, hi, best, start, ok = acct, acct, 0.0, d, False
        while d < days:
            line = min(hi, acct + 2000) - 2000; k = float(np.clip((bal - line) / 2000, 0.25, 1.0)) if scaled else 1.0
            pnl = x[d] * k; bal += pnl; d += 1; hi = max(hi, bal); best = max(best, pnl)
            if bal <= min(hi, acct + 2000) - 2000:
                break
            if bal - acct >= 3000 and best <= 0.5 * (bal - acct):
                ok = True; break
        net -= 49 * ((d - start) // 21 + 1)
        if not ok:
            continue
        net -= 149; bal, hi, wins = acct, acct, 0
        while d < days:
            line = min(hi, acct + 2000) - 2000; k = float(np.clip((bal - line) / 2000, 0.25, 1.0)) if scaled else 1.0
            pnl = x[d] * k; bal += pnl; d += 1; hi = max(hi, bal); wins += pnl >= 150
            if bal <= min(hi, acct + 2000) - 2000:
                break
            if wins >= 5 and bal > acct:
                w = min(0.5 * (bal - acct), 5000.0); net += 0.9 * w; bal -= w; wins = 0
    return net


def sim(vol, mode, scaled, paths=3000, days=504):
    rng = np.random.default_rng(11)
    r = b.to_numpy(); r = r / r.std() * vol / np.sqrt(252); r = r - {"full": 0.0, "zero": 1.0}[mode] * r.mean()
    out = []
    for _ in range(paths):
        idx = np.concatenate([np.arange(s, s + 10) % len(r) for s in rng.integers(0, len(r), days // 10 + 1)])[:days]
        out.append(run(r[idx] * 50_000.0, scaled))
    n = np.array(out); return {"mean": round(float(n.mean())), "P(net>0)": round(float((n > 0).mean()), 3)}


out = {}
for v in (0.10, 0.14, 0.18):
    k = f"vol {v:.0%}"; out[k] = {}
    for s in (False, True):
        f, z = sim(v, "full", s), sim(v, "zero", s)
        out[k]["buffer-scaled" if s else "constant"] = {"full": f, "zero": z, "edge value": f["mean"] - z["mean"]}
ev = [out[k]["buffer-scaled"]["edge value"] > out[k]["constant"]["edge value"] for k in out]
pp = [out[k]["buffer-scaled"]["full"]["P(net>0)"] >= out[k]["constant"]["full"]["P(net>0)"] for k in out]
out["pass"] = bool(sum(ev) >= 2 and all(pp))
print(json.dumps(out, indent=1)); (ROOT / "results/v99/dfp3_buffer.json").write_text(json.dumps(out, indent=1))

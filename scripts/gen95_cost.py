"""Gen95 (config/gen95_protocol.json): C* on cheap coins, risk-sized bounce. Writes results/gen95.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen92_capit.py")}
exec(open(ROOT / "scripts/gen92_capit.py").read().split("# L1 DVOL spike")[0], g)
inner = g["g"]; CS = inner["CS"]
B, CFD, fhp, d2h, IDX, dsh, P, R, bk = (g[k] for k in ("B", "CFD", "fhp", "d2h", "IDX", "dsh", "P", "R", "bk"))
BASE = dict(g["BASE"]); B0 = g["B0"]; oi_weights = inner["oi_weights"]
per = lambda h, d0: (dsh(h, d0, "2022-12-31"), dsh(h, "2023-01-01", "2024-12-31"), dsh(h, "2025-01-01", "2026-09-30"))
cw = CS.cstar_weights().copy(); cw["BNB"] = 0.0
a = cw.abs(); m = a.where(a > 0).mean(axis=1); cw = cw.where(a.ge(m * 0.5, axis=0), 0.0)
alts = [c for c in cw.columns if c not in ("BTC", "ETH")]
ROWS = []


def test(name, sleeve, h, d0):
    ref = per(BASE[sleeve], d0); p = per(h, d0); bA = dsh(bk({**BASE, sleeve: h}), "2022-01-01", "2026-09-30")
    r = {"test": name, "DEV": p[0], "TEST": p[1], "HOLD": p[2], "ref DEV": ref[0], "ref TEST": ref[1], "ref HOLD": ref[2], "book before": B0, "book after": bA}
    r["pass"] = bool(p[0] > 0 and p[1] > ref[1] and p[2] > ref[2] and bA > B0)
    ROWS.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


w1 = cw.copy(); w1[alts] = 0.0
test("G1 C* BTC/ETH only", "C*", fhp(d2h(w1), 3.3).reindex(IDX).fillna(0.0), "2020-01-01")
w2 = cw.copy(); w2[alts] = w2[alts] * 0.5
test("G2 C* alts at half weight", "C*", fhp(d2h(w2), 3.3).reindex(IDX).fillna(0.0), "2020-01-01")
wb = oi_weights(["BTC", "ETH"])
vol = R[["BTC", "ETH"]].rolling(30).std(); scale = (vol.rolling(365, min_periods=180).median() / vol).clip(upper=1.5).reindex(wb.index)
w3 = (wb * scale.fillna(1.0)).clip(upper=0.75)
test("G3 risk-sized bounce", "delev bounce", fhp(d2h(w3.reindex(columns=CFD).fillna(0.0)), 3.3).reindex(IDX).fillna(0.0), "2022-01-01")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen95.csv", index=False)
print("done", flush=True)

"""Shared harness for bf2 entrant tests (CFD costs): reference bf2 = bf sleeves + vol-managed indices + ridge ML (uncapped, as Gen234).
    import bf2lab as F; F.judge("name", hourly_pnl, out) ; F.cfd(daily_weights) ; F.book(extra, ridge=None)"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
END = "2026-09-30"
import os
if os.environ.get("QPL_COSTS", "measured") == "measured":     # from 2026-10-21: half the measured BrightFunded spread per side (cost check)
    import cfd_book as _CB
    _spec = pd.read_csv(sorted((ROOT / "research_data/firm_specs").glob("BrightFunded*20261021*.csv"))[-1], encoding="latin1")
    _meas = {s.split("/")[0].replace("XDG", "DOGE"): float(v) for s, v in zip(_spec["symbol"], _spec["spread_bp_median"]) if "/USD" in s}
    for _c in _CB.SPREAD.index:
        _CB.SPREAD[_c] = 0.5 * _meas[_c]
_g = {"__file__": str(ROOT / "scripts/gen196_bf_ridge.py")}; exec(open(ROOT / "scripts/gen196_bf_ridge.py").read().split("\nIS = (P6 + R1)")[0], _g)
CS, HB0, per, sh, HB_RIDGE, P6, R1, CB, IDXbf, sleeve = (_g[k] for k in ("CS", "HB0", "per", "sh", "hb", "P6", "R1", "CB", "IDXbf", "sleeve"))
_q = {"__file__": str(ROOT / "scripts/gen232_bf_p1.py")}; exec(open(ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], _q)
IS0 = (P6 + R1 + _q["p1"]()).rename("vol-managed indices"); hourly = _q["hourly"]
IDX1 = IDXbf.append(pd.DatetimeIndex([IDXbf[-1] + pd.Timedelta(hours=1)]))
cfd = lambda w: sleeve(CB.d2h(w.reindex(columns=CB.CFD).fillna(0.0), IDX1))


import os
if os.environ.get("QPL_REF", "v8") != "v7":                    # after Gen247: bf2's ridge uses the spot taker features (QPL_REF=v7: old)
    import ridge_live as _RL
    HB_RIDGE = cfd(_RL.predictions(END, spot=True).pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5)


def book(extra, ridge=None):
    r = HB_RIDGE if ridge is None else ridge
    return CS.portfolio_v5(pd.concat([HB0, IS0, r.rename("ridge ML")] + list(extra), axis=1).fillna(0.0))[0]


BF2 = book([]); REF = (sh(BF2, "2022-01-01", END), per(BF2, "2022-01-01"))


def judge(name, h, out, dev_start="2020-01-01", replace_ridge=False):
    s = per(h, dev_start); b = book([], ridge=h) if replace_ridge else book([h.rename(name)])
    B1, k1 = sh(b, "2022-01-01", END), per(b, "2022-01-01")
    r = {"sleeve D/T/H": np.round(s, 3).tolist(), "bf2": [round(B1, 3), np.round(k1, 3).tolist()]}
    r["pass"] = bool(s[0] > 0 and s[1] >= 0.5 and s[2] >= 0.3 and B1 > REF[0] and k1[1] >= REF[1][1] and k1[2] >= REF[1][2])
    out[name + " (bf2)"] = r; print(name, "bf2", r, flush=True)
    return r

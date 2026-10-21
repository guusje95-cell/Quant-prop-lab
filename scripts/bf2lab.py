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
    _CB.measured_costs()
_g = {"__file__": str(ROOT / "scripts/gen196_bf_ridge.py")}; exec(open(ROOT / "scripts/gen196_bf_ridge.py").read().split("\nIS = (P6 + R1)")[0], _g)
CS, HB0, per, sh, HB_RIDGE, P6, R1, CB, IDXbf, sleeve = (_g[k] for k in ("CS", "HB0", "per", "sh", "hb", "P6", "R1", "CB", "IDXbf", "sleeve"))
_q = {"__file__": str(ROOT / "scripts/gen232_bf_p1.py")}; exec(open(ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], _q)
IS0 = (P6 + R1 + _q["p1"]()).rename("vol-managed indices"); hourly = _q["hourly"]
IDX1 = IDXbf.append(pd.DatetimeIndex([IDXbf[-1] + pd.Timedelta(hours=1)]))
cfd = lambda w: sleeve(CB.d2h(w.reindex(columns=CB.CFD).fillna(0.0), IDX1))


import os
_BREF = os.environ.get("QPL_BF_REF", "bf2.4")
if os.environ.get("QPL_REF", "v8") != "v7":                    # after Gen247: bf2's ridge uses the spot taker features (QPL_REF=v7: old)
    import ridge_live as _RL                                   # bf2.1 (Gen301 A): + VRP; bf2.2 (Gen302 A): + VRP + calendar
    HB_RIDGE = cfd(_RL.predictions(END, spot=True, vrp=_BREF in ("bf2.1", "bf2.2", "bf2.3", "bf2.4"), cal=_BREF in ("bf2.2", "bf2.3", "bf2.4"))
                   .pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5)


ALTK_BF = []
if _BREF in ("bf2.3", "bf2.4"):                                # bf2.3 (Gen306 C = Gen270 rule): altcoin kimchi on 14 altcoin CFDs
    import alt_kimchi as _AK
    from qpl.lab import binance_pack as _B
    _aw = _AK.weights(END + " 23:00"); _ac = [c for c in _aw.columns if c in _CB.ALT_CFD]; _aw = _aw[_ac]
    _cost = pd.Series({c: _CB.ALT_SPREAD[c] + _CB.COMM for c in _ac}) / 1e4
    _r = _B.panel("close", "1h", _ac).loc[:END + " 23:00"].pct_change(fill_method=None).fillna(0.0)
    _held = _aw.reindex(_aw.index.append(pd.DatetimeIndex([_aw.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(_r.index.floor("D")).set_axis(_r.index).fillna(0.0)
    ALTK_BF = [((_held * _r).sum(axis=1) - _held.diff().abs().fillna(_held.abs()).mul(_cost, axis=1).sum(axis=1)).reindex(IDXbf).fillna(0.0).rename("alt kimchi")]

if _BREF == "bf2.4":                                           # bf2.4 (Gen317): invvol premium carry on cfd_book.CARRY_CFD
    import crypto_sleeves as _CS
    _U = _CB.CARRY_CFD; _cw = _CS.premium_breadth_weights(coins=_U, invvol=True); _H = _CS._breadth_close(_U)
    _r2 = _H.pct_change(fill_method=None).fillna(0.0)
    _h2 = _cw.reindex(_cw.index.append(pd.DatetimeIndex([_cw.index[-1] + pd.Timedelta(days=1)]))).reindex(columns=_U).shift(1).reindex(_H.index.floor("D")).set_axis(_H.index).fillna(0.0)
    ALTK_BF = ALTK_BF + [((_h2 * _r2).sum(axis=1) - _h2.diff().abs().fillna(_h2.abs()).mul((_CB.CARRY_SPREAD + _CB.COMM) / 1e4, axis=1).sum(axis=1)).reindex(IDXbf).fillna(0.0).rename("premium carry BF")]


def book(extra, ridge=None):
    r = HB_RIDGE if ridge is None else ridge
    return CS.portfolio_v5(pd.concat([HB0, IS0, r.rename("ridge ML")] + ALTK_BF + list(extra), axis=1).fillna(0.0))[0]


BF2 = book([]); REF = (sh(BF2, "2022-01-01", END), per(BF2, "2022-01-01"))


def judge(name, h, out, dev_start="2020-01-01", replace_ridge=False):
    s = per(h, dev_start); b = book([], ridge=h) if replace_ridge else book([h.rename(name)])
    B1, k1 = sh(b, "2022-01-01", END), per(b, "2022-01-01")
    r = {"sleeve D/T/H": np.round(s, 3).tolist(), "bf2": [round(B1, 3), np.round(k1, 3).tolist()]}
    r["pass"] = bool(s[0] > 0 and s[1] >= 0.5 and s[2] >= 0.3 and B1 > REF[0] and k1[1] >= REF[1][1] and k1[2] >= REF[1][2])
    out[name + " (bf2)"] = r; print(name, "bf2", r, flush=True)
    return r

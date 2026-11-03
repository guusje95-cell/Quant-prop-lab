"""Positions of the 8 equity-index sleeves of the exact daily-flat futures book (DF-3: P1, R1, T1, T2, FC, MM, OIL, K3; ES + NQ only),
re-derived from the research code (unchanged logic), for a live daily-flat bot (Topstep / Lucid micros, or US500 / US100 CFDs).

Session d = 18:00 ET of the previous trading day until 16:00 ET of d (flat 16:00-18:00 ET and at weekends).
  calendar T1 / T2 / FC / MM / OIL:  0.5 x mask_d per market (Gen203 ESNQ), whole session d
  K3:                               ES only, W_d (Gen143 k3(5))
  P1:                               w decided at 16:00 ET of the previous day (IBS < 0.3), whole session d
  R1:                               ES / NQ / RTY / YM; w decided at 14:00 ET: until 14:00 of d the previous day's w, from 14:00 of d the new w
Book weights per sleeve = fbook rule over the 8 daily-flat sleeves (1/sd on 2010-22, positive Sharpe), level = 10% / 60-day vol,
cap 3x, lagged one day. Selftest: hourly gross P&L of these positions on the patched bars vs the sleeves' own P&L (before costs).

    python scripts/v99/dailyflat_positions.py --selftest"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
os.environ["QPL_DAILY_FLAT"] = "1"
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99"))
import dailyflat  # noqa: E402

F = dailyflat.patch()
EQ8 = ["P1", "R1", "T1", "T2", "FC", "MM", "OIL", "K3"]
MK = ["ES", "NQ"]
MK4 = ["ES", "NQ", "RTY", "YM"]                                           # R1 trades all four indices (Gen155 EQ)


def _ns(script, cut):
    g = {"__file__": str(ROOT / "scripts" / script), "__name__": "x"}
    exec((ROOT / "scripts" / script).read_text().split(cut)[0], g); return g


def _ext(x):
    """append the next weekday (row of NaN) so that a one-day shift also yields the next session's value (live targets)"""
    nxt = x.index[-1] + pd.offsets.BDay(1)
    return x.reindex(x.index.append(pd.DatetimeIndex([nxt])))


def session_positions() -> dict[str, pd.DataFrame]:
    """sleeve -> DataFrame (index: trading date d, columns ES / NQ) of the position held in session d; R1 returns two frames."""
    g203 = _ns("gen203_universe.py", "\nres = {}")
    IX, M = g203["IX"], g203["M"]
    out = {n: pd.DataFrame({r: M[n].reindex(IX).fillna(0.0) * 0.5 for r in MK}) for n in ("T1", "T2", "FC", "MM", "OIL")}
    g143 = _ns("gen143_families.py", 'c = {"__file__": str(ROOT / "scripts/gen119_cot.py")}')
    RK, VK = g143["RK"], g143["VK"]; W = pd.Series(0.0, index=RK.index)
    for _, gg in RK.groupby(RK.index.to_period("M")):
        if len(gg) < 8:
            continue
        d0 = gg.index[-6]; mtd = (1 + gg.loc[:d0]).prod() - 1
        W.loc[gg.index[-5:]] = (-1.0 if mtd.ES > mtd.ZN else 1.0) * 0.15 / VK.loc[d0]
    out["K3"] = pd.DataFrame({"ES": W, "NQ": 0.0})
    p1, p1raw = {}, {}
    for r in MK:
        f = F.front(r); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod(); wk = (t.wd < 5).to_numpy()
        m = wk & (t.h == 15).to_numpy(); c = pz[m].groupby(t.date[m]).last()
        rth = wk & (t.h >= 9).to_numpy() & (t.h < 16).to_numpy()
        hi = np.maximum(pz[rth].groupby(t.date[rth]).max().reindex(c.index), c); lo = np.minimum(pz[rth].groupby(t.date[rth]).min().reindex(c.index), c)
        w1 = 0.5 * (((c - lo) / (hi - lo)) < 0.3).astype(float).where(hi > lo, 0.0)
        p1[r] = _ext(w1).shift(1)                                                                        # decided on the previous day
        p1raw[r] = w1
    out["P1"] = pd.DataFrame(p1).fillna(0.0); out["P1 decided 16:00"] = pd.DataFrame(p1raw).fillna(0.0)
    g155 = _ns("gen155_r1_refine.py", "SN = {r: snaps")
    r1 = {}
    for r in MK4:
        c, hi, lo, _ = g155["snaps"](r); ibs = (c - lo) / (hi - lo); ret = c.pct_change()
        z = [g155["rsi2"](c) < 10, c <= c.rolling(5).min(), c.diff().lt(0).rolling(3).sum() == 3, ibs < 0.3]
        sig = (sum(x.astype(float) for x in z) / 4).where(hi > lo, 0.0)
        mult = (ret.rolling(250, min_periods=120).std() / ret.rolling(20).std()).clip(upper=2)
        r1[r] = (0.25 * sig * mult).fillna(0.0)
    new = pd.DataFrame(r1); out["R1 from 14:00"] = new; out["R1 until 14:00"] = _ext(new).shift(1).fillna(0.0)
    return out


def hourly(pos: dict) -> dict[str, pd.DataFrame]:
    """hourly position per sleeve on the patched front bars (bar-start label). Calendar sleeves and K3 by CME trade date (as the
    research's daily_book); P1 and R1 by their decision time (P1: 16:00 ET, R1: 14:00 ET), holding the latest decision made at or
    before the bar's start. Bars the patch zeroes (16:00 ET bar unless QPL_FLAT_FROM=17, closures) carry no P&L either way."""
    H = {}
    for r in MK4:
        f = F.front(r); t = F.ny(f.index); td = F.trade_date(f.index)
        et = pd.DatetimeIndex(f.index).tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
        for n, P in pos.items():
            if n.startswith("R1") or n.startswith("P1") or r not in P:
                continue
            H.setdefault(n, {})[r] = pd.Series(P[r].reindex(td).fillna(0.0).to_numpy(), index=f.index)
        for n, key, hh in (("P1", "P1 decided 16:00", 16), ("R1", "R1 from 14:00", 14)):
            if r not in pos[key]:
                continue
            w = pos[key][r]; dec = pd.Series(w.to_numpy(), index=pd.DatetimeIndex(w.index) + pd.Timedelta(hours=hh)).sort_index()
            H.setdefault(n, {})[r] = pd.Series(dec.reindex(et, method="ffill").fillna(0.0).to_numpy(), index=f.index)
    return {n: pd.DataFrame(v).fillna(0.0) for n, v in H.items()}


def selftest() -> dict:
    pos = session_positions(); H = hourly(pos)
    Q = pd.read_parquet(ROOT / ("results/v99/df7_sleeves.parquet" if os.environ.get("QPL_FLAT_FROM") == "17" else "results/v99/df1_sleeves.parquet"))
    out = {}
    for n, Hp in H.items():
        g = sum(Hp[r].dropna().pipe(lambda p: (p * F.front(r).r.reindex(p.index).fillna(0.0)).groupby(F.trade_date(p.index)).sum()) for r in Hp.columns)
        d = g[g.index.weekday < 5]
        x = pd.concat([d, Q[n]], axis=1, keys=["gross from positions", "sleeve"]).loc["2011":"2026-09-30"].dropna()
        out[n] = {"corr": round(float(x.corr().iloc[0, 1]), 4), "monthly corr": round(float(x.resample("ME").sum().corr().iloc[0, 1]), 4), "mean gross - sleeve (bp/day)": round(float((x.iloc[:, 0] - x.iloc[:, 1]).mean() * 1e4), 3)}
    return out


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        r = selftest(); print(json.dumps(r, indent=1)); (ROOT / "results/v99/dailyflat_positions_selftest.json").write_text(json.dumps(r, indent=1))

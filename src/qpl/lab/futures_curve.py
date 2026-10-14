"""Commodity futures CURVE data for the curve-momentum strategy (de Groot, Karstanje & Zhou 2014).

pysystemtrade's multiple_prices files hold up to three contracts per date: CARRY, PRICE and FORWARD (each with a YYYYMM00
contract code). We sort the distinct contracts by expiry into slots 0 (nearest), 1, 2 and build, per slot, a daily
total-return index that always follows ONE contract from day to day (return of the contract held yesterday, wherever it
sits today), plus the curve slope of each slot vs. the slot before it:  slope_k = (f_{k-1} - f_k) / (f_k * (tau_k - tau_{k-1}))
(positive = backwardated). Slot 0 gets slot 1's slope (flat extrapolation, the paper uses cubic extrapolation).

Bars columns are '<COMMODITY>#<slot>', e.g. 'CORN#0'; Bars.extra['slope'] holds the slopes with the same columns.
Source: robcarver17/pysystemtrade data/futures/multiple_prices_csv (GPL-3; local copy or GitHub raw on your PC)."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / "data/raw/ext/pysystemtrade/data/futures/multiple_prices_csv"
GH = "https://raw.githubusercontent.com/robcarver17/pysystemtrade/master/data/futures/multiple_prices_csv"
COMMODITIES = ["CRUDE_W", "BRENT_W", "HEATOIL", "GASOILINE", "GASOIL", "GAS_US", "GOLD", "SILVER", "COPPER", "PLAT", "PALLAD",
               "ALUMINIUM_LME", "ZINC_LME", "NICKEL_LME", "LEAD_LME", "CORN", "WHEAT", "REDWHEAT", "SOYBEAN", "SOYMEAL", "SOYOIL",
               "SUGAR11", "COFFEE", "COCOA", "COTTON2", "LIVECOW", "FEEDCOW", "LEANHOG"]
CACHE = ROOT / "data/lab/futures_curve.parquet"


def _read(sym: str) -> pd.DataFrame:
    f = LOCAL / f"{sym}.csv"
    if f.exists():
        df = pd.read_csv(f)
    else:
        import requests
        r = requests.get(f"{GH}/{sym}.csv", timeout=120); r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
    df["DATETIME"] = pd.to_datetime(df["DATETIME"])
    return df.groupby(df["DATETIME"].dt.normalize()).last().drop(columns="DATETIME")


def _tau(code) -> float:
    c = int(code); y, m = c // 10000, (c // 100) % 100
    return y + (m - 1) / 12.0


def build_one(sym: str, nslots: int = 3):
    df = _read(sym)
    dates = df.index
    # contracts available per day: {code: price}
    avail = []
    for _, row in df.iterrows():
        d = {}
        for p, c in (("CARRY", "CARRY_CONTRACT"), ("PRICE", "PRICE_CONTRACT"), ("FORWARD", "FORWARD_CONTRACT")):
            if pd.notna(row.get(p)) and pd.notna(row.get(c)) and row[p] > 0:
                d[int(row[c])] = float(row[p])
        avail.append(d)
    n = len(dates); ret = np.full((n, nslots), np.nan); slope = np.full((n, nslots), np.nan)
    roll = np.zeros((n, nslots), dtype=bool)
    held = [None] * nslots
    for t in range(n):
        codes = sorted(avail[t])
        for k in range(nslots):
            c_prev = held[k]
            if t > 0 and c_prev is not None and c_prev in avail[t] and c_prev in avail[t - 1]:
                ret[t, k] = avail[t][c_prev] / avail[t - 1][c_prev] - 1
            elif t > 0 and c_prev is not None:
                ret[t, k] = 0.0                          # contract left the file: no observable return that day
            new = codes[k] if k < len(codes) else None
            roll[t, k] = t > 0 and new != held[k]
            held[k] = new
        for k in range(1, min(nslots, len(codes))):
            f0, f1 = avail[t][codes[k - 1]], avail[t][codes[k]]
            dt = _tau(codes[k]) - _tau(codes[k - 1])
            slope[t, k] = (f0 - f1) / (f1 * dt) if dt > 0 else np.nan
        if len(codes) >= 2:
            slope[t, 0] = slope[t, 1]
    cols = [f"{sym}#{k}" for k in range(nslots)]
    r = pd.DataFrame(ret, index=dates, columns=cols)
    r = r.where(r.abs() < 0.5)                           # drop bad prints
    s = pd.DataFrame(slope, index=dates, columns=cols)
    return r, s, pd.DataFrame(roll, index=dates, columns=cols)


def build(symbols=None, refresh=False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """-> (daily returns per slot, slope per slot, roll flag per slot)."""
    if CACHE.exists() and not refresh and symbols is None:
        d = pd.read_parquet(CACHE)
        if "roll" in d.columns.get_level_values(0):
            return d.xs("ret", axis=1, level=0), d.xs("slope", axis=1, level=0), d.xs("roll", axis=1, level=0).astype(bool)
    R, S, RL = [], [], []
    for sym in symbols or COMMODITIES:
        try:
            r, s, rl = build_one(sym); R.append(r); S.append(s); RL.append(rl)
        except Exception as e:  # missing file etc.
            print("curve", sym, "skipped:", e)
    R = pd.concat(R, axis=1).sort_index(); S = pd.concat(S, axis=1).sort_index()
    RL = pd.concat(RL, axis=1).sort_index().reindex(S.index).fillna(False).astype(bool)
    if symbols is None:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        pd.concat({"ret": R, "slope": S, "roll": RL.astype(float)}, axis=1).to_parquet(CACHE)
    return R, S, RL


def bars():
    from qpl.lab.data import Bars, PPY
    R, S, RL = build()
    c = 100 * (1 + R.fillna(0)).cumprod().where(R.notna().cumsum() > 0)
    nan = c * np.nan
    return Bars("Commodity futures curve (3 contracts)", "1d", c, c, c, c, nan, PPY["1d_tradfi"],
                {"slope": S.reindex(c.index), "roll": RL.reindex(c.index).fillna(False)})

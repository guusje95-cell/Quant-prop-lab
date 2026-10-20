"""Gen157 (config/gen157_protocol.json): relative reversal NQ/RTY/YM vs ES. Writes results/gen157.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
TUNE, JUDGE = ("2010-06-01", "2022-12-31"), ("2023-01-01", "2026-09-30")
S = lambda p, w: F.sharpe(p, *w)
D = {r: F.daily(r) for r in ("ES", "NQ", "RTY", "YM")}
R = pd.DataFrame({r: D[r].r for r in D}).dropna(); R = R[R.index.weekday < 5]
C = pd.DataFrame({r: D[r].cost for r in D}).reindex(R.index).ffill(); RL = pd.DataFrame({r: D[r].roll for r in D}).reindex(R.index).fillna(0)


def pair(x, L, th):
    beta = (R[x].rolling(120).cov(R.ES) / R.ES.rolling(120).var()).shift(1)
    sp = R[x] - beta * R.ES; sd = sp.rolling(120).std()
    z = sp.rolling(L).sum() / (sd * np.sqrt(L))
    ent = pd.Series(np.where(z < -th, 1.0, np.where(z > th, -1.0, 0.0)), index=R.index)
    pos = ent.shift(1).rolling(L, min_periods=1).mean()                       # traded at the close of t+1, held L days (overlapping)
    size = (0.10 / 3) / (sd * np.sqrt(252))
    wx = (pos * size).shift(1).fillna(0.0); we = -wx * beta.fillna(1.0)          # held during the next day
    pnl = wx * R[x] + we * R.ES
    cost = (wx.diff().abs() + 2 * wx.abs() * RL[x]) * C[x] + (we.diff().abs() + 2 * we.abs() * RL.ES) * C.ES
    return (pnl - cost.fillna(0.0)).fillna(0.0)


def sleeve(L, th):
    return sum(pair(x, L, th) for x in ("NQ", "RTY", "YM"))


if __name__ == "__main__":
    rep, best = [], None
    for L in (3, 5, 10):
        for th in (1.0, 1.5):
            p = sleeve(L, th); st = S(p, TUNE); rep.append({"L": L, "th": th, "tune": round(st, 3), "2023-26": round(S(p, JUDGE), 3)}); print(rep[-1], flush=True)
            if best is None or st > best[0]:
                best = (st, rep[-1], p)
    out = {"grid": rep, "chosen": best[1], "enters": bool(best[0] > 0.3)}
    if out["enters"]:
        src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
        exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
        base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); base["RV"] = best[2]
        b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 0.842)
    print(json.dumps({k: v for k, v in out.items() if k != "grid"})); json.dump(out, open(ROOT / "results/gen157.json", "w"), indent=1)

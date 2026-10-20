"""Gen154 (config/gen154_protocol.json): intraday return periodicity, 26 futures hourly. Writes results/gen154.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
TUNE, JUDGE = ("2010-06-01", "2022-12-31"), ("2023-01-01", "2026-09-30")
S = lambda p, w: F.sharpe(p, *w)
ROOTS = F.NONCRYPTO


def prep(root):
    f = F.front(root); t = F.ny(f.index); r = f.r.astype(float)
    df = pd.DataFrame({"r": r.to_numpy(), "h": t.h.to_numpy(), "d": F.trade_date(f.index)}, index=f.index)
    df["cost"] = F.cost_frac(root, f.close.astype(float)).to_numpy() if "close" in f else F.daily(root).cost.reindex(df.d).to_numpy()
    df["vol"] = df.r.rolling(24 * 60, min_periods=24 * 20).std().shift(1)
    return df


def pnl(df, N, k):
    out = []
    piv = df.pivot_table(index="d", columns="h", values="r", aggfunc="sum")
    m = piv.rolling(N, min_periods=int(N * 0.8)).mean().shift(1); s = piv.rolling(N, min_periods=int(N * 0.8)).std().shift(1)
    tt = m / (s / np.sqrt(N))
    sig = np.sign(tt).where(tt.abs() > k, 0.0)
    st = sig.stack().rename("sig"); x = df.join(st, on=["d", "h"])
    w = (x.sig.fillna(0.0) * 0.10 / (x.vol * np.sqrt(24 * 252)) / len(ROOTS)).where(lambda z: np.isfinite(z), 0.0)
    p = w * x.r.fillna(0.0) - w.diff().abs().fillna(0.0) * x.cost.ffill()
    return p.groupby(x.d).sum()


if __name__ == "__main__":
    P = {r: prep(r) for r in ROOTS}; print("loaded", flush=True)
    rep, best = [], None
    for N in (20, 60, 250):
        for k in (0, 1, 2):
            p = pd.concat([pnl(P[r], N, k) for r in ROOTS], axis=1).fillna(0.0).sum(axis=1); p = p[p.index.weekday < 5]
            st, sj = S(p, TUNE), S(p, JUDGE); rep.append({"N": N, "k": k, "tune": round(st, 3), "2023-26": round(sj, 3)}); print(rep[-1], flush=True)
            if best is None or st > best[0]:
                best = (st, N, k, p)
    out = {"grid": rep, "best": {"N": best[1], "k": best[2], "tune": round(best[0], 3), "2023-26": round(S(best[3], JUDGE), 3)}, "enters": bool(best[0] > 0.3)}
    if out["enters"]:
        src = open(ROOT / "scripts/gen140_optimise.py").read(); h = {"__file__": str(ROOT / "scripts/gen140_optimise.py")}
        exec(src.split("GRID = {")[0], h); exec("def build(P, method):" + src.split("def build(P, method):")[1].split("Pbest = pd.DataFrame")[0], h)
        base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); base["IP"] = best[3]
        book = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(book, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 0.815)
    print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen154.json", "w"), indent=1)

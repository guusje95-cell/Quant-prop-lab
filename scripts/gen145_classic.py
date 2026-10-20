"""Gen145 (config/gen145_protocol.json): value, seasonality, multi-speed trend, 52-week high, continuous carry. Writes results/gen145.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
src = open(ROOT / "scripts/gen143_families.py").read()
g = {"__file__": str(ROOT / "scripts/gen143_families.py")}
exec(src.split("R2 = pd.DataFrame")[0], g)
F, S, TUNE, JUDGE, build, D, daily_book, R24, SD, ME, PX, xs = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "build", "D", "daily_book", "R24", "SD", "ME", "PX", "xs"))
ALL = list(R24.columns); LP = np.log(PX)


def v1(yrs, n):
    lag = int(252 * yrs); past = PX.shift(lag - 126).rolling(252, min_periods=200).mean()
    return xs(-(LP - np.log(past)), ALL, n)


MR = R24.fillna(0.0).groupby(R24.index.to_period("M")).apply(lambda x: (1 + x).prod() - 1)


def s1(N, n):
    sc = pd.DataFrame(np.nan, index=MR.index, columns=ALL)
    for i, p in enumerate(MR.index):
        nxt = p + 1; prev = [nxt - 12 * k for k in range(1, N + 1)]
        if prev[-1] < MR.index[0]:
            continue
        sc.loc[p] = MR.reindex(prev).mean()
    sc.index = [ME.get(p, pd.NaT) for p in sc.index]
    return xs(sc[sc.index.notna()].reindex(R24.index).ffill(), ALL, n)


VOL = R24.ewm(span=35, min_periods=30).std()
SPEEDS = {"fast": [(8, 32), (16, 64)], "slow": [(32, 128), (64, 256)], "all": [(8, 32), (16, 64), (32, 128), (64, 256)]}


def e1(speed):
    fc = 0
    for a, b in SPEEDS[speed]:
        raw = (PX.ewm(span=a).mean() - PX.ewm(span=b).mean()) / (PX * VOL)
        fc = fc + (raw / raw.loc[:TUNE[1]].abs().stack().mean()).clip(-2, 2)
    fc = fc / len(SPEEDS[speed])
    W = (fc * 0.10 / (VOL * np.sqrt(252)) / len(ALL)).where(np.isfinite, 0.0)
    return daily_book(W.shift(1).fillna(0.0), ALL)


def w1(n):
    return xs(PX / PX.rolling(252, min_periods=240).max(), ALL, n)


CR = pd.DataFrame({r: np.log(D[r].near_far) / F.SPEC[r][3] for r in ALL}).reindex(R24.index)


def c5(sm):
    c = CR.rolling(sm, min_periods=1).mean() if sm > 1 else CR
    z = c / c.loc[:TUNE[1]].abs().median()
    fc = z.clip(-2, 2)
    W = (fc * 0.10 / (VOL * np.sqrt(252)) / len(ALL)).where(np.isfinite, 0.0)
    return daily_book(W.shift(1).fillna(0.0), ALL)


FAM = {"V1": [(v1, {"yrs": y, "n": n}) for y in (3, 5) for n in (4, 6)],
       "S1": [(s1, {"N": N, "n": n}) for N in (5, 10) for n in (4, 6)],
       "E1": [(e1, {"speed": s}) for s in SPEEDS],
       "W1": [(w1, {"n": n}) for n in (4, 6)],
       "C5": [(c5, {"sm": s}) for s in (1, 21, 63)]}
if __name__ == "__main__":
    rep, enter, allp = {}, {}, {}
    for name, opts in FAM.items():
        res = []
        for fn, prm in opts:
            p = fn(**prm); res.append((S(p, TUNE), prm, p))
            print(name, prm, round(res[-1][0], 3), round(S(p, JUDGE), 3), flush=True)
        res.sort(key=lambda x: -x[0]); s, prm, p = res[0]; allp[name] = p
        rep[name] = {"best": prm, "tune 2010-22": round(s, 3), "2023-26": round(S(p, JUDGE), 3), "enters": bool(s > 0.3)}
        if s > 0.3:
            enter[name] = p
    exec(open(ROOT / "scripts/gen140_optimise.py").read().split("GRID = {")[0], g)
    base = pd.read_parquet(ROOT / "results/gen143_entrants.parquet")
    B140 = json.load(open(ROOT / "results/gen140.json"))["chosen per sleeve"]; FN = {"F3": g["f3"], "F5": g["f5"], "G1": g["g1"], "P1": g["p1"], "A3": g["a3"]}
    b0 = {k: FN[k](**{kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in v["params"].items()}) for k, v in B140.items()}
    b0.update({c: base[c] for c in base})
    ref = build(pd.DataFrame(b0), "sharpe-weighted"); book = build(pd.DataFrame({**b0, **enter}), "sharpe-weighted")
    out = {"families": rep, "entered": list(enter), "reference (Gen143 book, same code) 2023-26": round(S(ref, JUDGE), 3),
           "book 2023-26": round(S(book, JUDGE), 3), "book 2010-17 / 2018-22": [round(F.sharpe(book, *F.SPLITS[0]), 3), round(F.sharpe(book, *F.SPLITS[1]), 3)]}
    out["adopt"] = bool(out["book 2023-26"] > 0.674)
    print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen145.json", "w"), indent=1)
    book.to_frame("book").to_parquet(ROOT / "results/gen145_book.parquet"); pd.DataFrame(allp).to_parquet(ROOT / "results/gen145_sleeves.parquet")

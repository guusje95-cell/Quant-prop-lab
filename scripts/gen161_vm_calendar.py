"""Gen161 (config/gen161_protocol.json): vol-managed equity calendar sleeves. Writes results/gen161.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
g = {"__file__": str(ROOT / "scripts/gen159_fomc_cycle.py")}; exec(open(ROOT / "scripts/gen159_fomc_cycle.py").read().split("FAM = {")[0], g)
F, S, TUNE, JUDGE, D, daily_book, h, EQ, IX = (g[k] for k in ("F", "S", "TUNE", "JUDGE", "D", "daily_book", "h", "EQ", "IX"))
k = {"__file__": str(ROOT / "scripts/gen146_equity.py")}; exec(open(ROOT / "scripts/gen146_equity.py").read().split("FAM = {")[0], k)
R = pd.DataFrame({r: D[r].r for r in EQ}).reindex(IX)
raw = (0.15 / (R.rolling(20).std() * np.sqrt(252))).shift(1); MULT = (raw / raw.loc[:TUNE[1]].stack().median()).clip(upper=2).fillna(1.0)


def masks():
    t1 = pd.Series(0.0, index=IX); per = IX.to_period("M"); starts = np.where(~pd.Series(per).duplicated().to_numpy())[0]
    for i in starts[1:]:
        t1.iloc[max(0, i - 2):i + 3] = 1.0                      # Gen146 chosen T1 (2 before, 3 after)
    t2 = pd.Series(0.0, index=IX)
    for d in k["hol"]:
        j = IX.searchsorted(d)
        if 0 < j <= len(IX):
            t2.iloc[j - 1:j] = 1.0                              # Gen146 chosen T2 (1 session)
    return {"T1": t1, "T2": t2, "FC": pd.Series(g["mask_fc"]((2, 4, 6)).astype(float), index=IX), "MM": pd.Series(g["mask_mm"](-1, 1).astype(float), index=IX)}


M = masks()


def sleeves(vm):
    return {n: daily_book(pd.DataFrame({r: m * 0.25 * (MULT[r] if vm else 1.0) for r in EQ}), EQ) for n, m in M.items()}


res = {}
for v in (False, True):
    sl = sleeves(v); comb = pd.DataFrame(sl).fillna(0.0).sum(axis=1)
    res["vm" if v else "const"] = {"tune": round(S(comb, TUNE), 3), "2023-26": round(S(comb, JUDGE), 3), "per sleeve tune/2023-26": {n: [round(S(p, TUNE), 2), round(S(p, JUDGE), 2)] for n, p in sl.items()}}
    print(v, res["vm" if v else "const"], flush=True)
ch = max(("const", "vm"), key=lambda c: res[c]["tune"]); out = {"variants": res, "chosen": ch}
if ch == "vm":
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); sl = sleeves(True)
    for n in M:
        base[n] = sl[n]
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 0.908)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen161_book.parquet")
print(json.dumps({x: y for x, y in out.items() if x != "variants"})); json.dump(out, open(ROOT / "results/gen161.json", "w"), indent=1)

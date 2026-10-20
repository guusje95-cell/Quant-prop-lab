"""Gen173 (config/gen173_protocol.json): overnight-only holding of the equity calendar sleeves. Writes results/gen173.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
c = {"__file__": str(ROOT / "scripts/gen161_vm_calendar.py")}; exec(open(ROOT / "scripts/gen161_vm_calendar.py").read().split("res = {}")[0], c)
F, S, TUNE, JUDGE, h, EQ, M, sleeves = (c[k] for k in ("F", "S", "TUNE", "JUDGE", "h", "EQ", "M", "sleeves"))
NIGHT = {}
for r in EQ:
    f = F.front(r); t = F.ny(f.index); pz = (1 + f.r.fillna(0.0)).cumprod(); wk = (t.wd < 5).to_numpy()
    pick = lambda hh: pz[wk & (t.h == hh).to_numpy()].groupby(t.date[wk & (t.h == hh).to_numpy()]).last()
    c16, c09 = pick(15), pick(8)
    prev16 = c16.shift(1).reindex(c09.index)                        # 16:00 of the previous trading day
    ok = (c09.index.to_series() - c16.index.to_series().shift(1).reindex(c09.index)).dt.days.le(4)
    NIGHT[r] = ((c09 / prev16 - 1).where(ok), F.daily(r).cost.reindex(c09.index).ffill())


def night(mask):
    out = []
    for r in EQ:
        ret, cost = NIGHT[r]; on = mask.reindex(ret.index).fillna(0.0)
        out.append(0.25 * on * (ret.fillna(0.0) - 2 * cost))
    p = pd.concat(out, axis=1).fillna(0.0).sum(axis=1); return p[p.index.weekday < 5]


full = sleeves(False); nt = {n: night(m) for n, m in M.items()}
res = {}
for name, sl in (("full", full), ("night", nt)):
    comb = pd.DataFrame(sl).fillna(0.0).sum(axis=1)
    res[name] = {"tune": round(S(comb, TUNE), 3), "2023-26": round(S(comb, JUDGE), 3), "per sleeve": {n: [round(S(p, TUNE), 2), round(S(p, JUDGE), 2)] for n, p in sl.items()}}
    print(name, res[name], flush=True)
ch = max(res, key=lambda k: res[k]["tune"]); out = {"variants": res, "chosen": ch}
if ch == "night":
    base = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
    for n in M:
        base[n] = nt[n]
    b = h["build"](base, "sharpe-weighted"); out["book 2023-26"] = round(S(b, JUDGE), 3); out["adopt"] = bool(out["book 2023-26"] > 1.102)
    out["book 2010-17 / 2018-22"] = [round(F.sharpe(b, *F.SPLITS[0]), 3), round(F.sharpe(b, *F.SPLITS[1]), 3)]
    if out["adopt"]:
        base.to_parquet(ROOT / "results/book_sleeves_current.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen173_book.parquet")
print(json.dumps({k: v for k, v in out.items() if k != "variants"})); json.dump(out, open(ROOT / "results/gen173.json", "w"), indent=1)

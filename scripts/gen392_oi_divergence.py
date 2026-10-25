"""Gen392 (config/gen392_protocol.json). Writes results/gen392.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen390_breadth_regime.py").read().split("\nref_book = pd.read_parquet(ROOT")[0]
g = {"__file__": str(ROOT / "scripts/gen390_breadth_regime.py")}; exec(compile(src, "g390", "exec"), g)
POOL, idx, dd, shp, per, unit, END, CS, base, K1, days, pnl_daily = (g[k] for k in ("POOL", "idx", "dd", "shp", "per", "unit", "END", "CS", "base", "K1", "days", "pnl_daily"))
ref_book = pd.read_parquet(ROOT / "results/gen385_book_hourly.parquet")["book"]; REF = (shp(ref_book), per(ref_book))
B = g["B"]
def oi_events(c, oi_sign, px_sign, th=0.10, hold=2, size=0.5):
    m = B.metrics(c)["sum_open_interest_value"].pipe(lambda z_: z_.where(z_ > 0)).resample("1h").last().ffill(); px = B.k5(c).close.resample("1h").last()
    dd_ = pd.date_range("2021-12-01", END); t = dd_ + pd.Timedelta(days=1) - pd.Timedelta(minutes=5)
    f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
    doi = f(m, t) / f(m, t - pd.Timedelta(days=1)) - 1; dpx = f(px, t) / f(px, t - pd.Timedelta(days=1)) - 1
    sig = pd.Series(((oi_sign * doi) > th) & ((px_sign * dpx) > 0), index=dd_)
    return sig.astype(float).rolling(hold, min_periods=1).max() * size
NEW = {"Q1 squeeze fade": lambda c: -oi_events(c, -1, 1), "Q2 trapped shorts": lambda c: oi_events(c, 1, -1), "Q3 euphoria fade": lambda c: -oi_events(c, 1, 1)}
res = {}
for k, fn in NEW.items():
    w = pd.DataFrame({c: fn(c) for c in ("BTC", "ETH", "SOL")}); POOL[k] = pnl_daily(w).reindex(idx).fillna(0.0)
    res[k] = {"2022 / 2023-24 / 2025-26": per(POOL[k]), "event days": int((w.diff().fillna(w) > 0).sum().sum())}
    print(k, res[k], flush=True)
D = pd.DataFrame({k: dd(v) for k, v in POOL.items()}).loc["2022":END].fillna(0.0); D24 = D.loc[:"2024"]; K1d = dd(K1).loc["2022":"2024"]
cand = [k for k in D if abs(float(pd.concat([D24[k], K1d], axis=1).corr().iloc[0, 1])) < 0.3 and D24[k].std() > 0]
def bsr(keys):
    x = (D24[keys] / D24[keys].std()).sum(axis=1); return float(x.mean() / x.std() * np.sqrt(365))
kept, cur, steps = [], -9.0, []
while True:
    best = max(((k, bsr(kept + [k])) for k in cand if k not in kept), key=lambda t: t[1], default=(None, -9))
    if best[0] is None or best[1] < cur + 0.05:
        break
    kept.append(best[0]); cur = best[1]; steps.append([best[0], round(cur, 3)])
sdv = D24[kept].std(); bh = sum(POOL[k] / sdv[k] for k in kept); bh = bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
s3 = open(ROOT / "scripts/gen383_ensembles.py").read().split("T = {")[0]; g3 = {"__file__": str(ROOT / "scripts/gen383_ensembles.py")}; exec(compile(s3, "g383", "exec"), g3)
b = unit(CS.portfolio_v5(base.assign(**{"trend 4h": g3["te"], "alt kimchi": g3["ke"], "diversifier basket": bh.reindex(base.index).fillna(0.0)}))[0]); B1, k = shp(b), per(b)
out = {"reference v9.2": [REF[0], REF[1]], "new": res, "steps": steps, "basket": per(bh), "book": [B1, k], "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen392.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))

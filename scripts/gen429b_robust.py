"""Gen429b (descriptive): robustness of the Gen429 A funding-interval fade (no variant is chosen from this). Writes results/gen429b.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen429_funding_interval.py").read().split("\nREF_R = ")[0]
g = {"__file__": str(ROOT / "scripts/gen429_funding_interval.py")}; exec(compile(src, "g429", "exec"), g)
EV, DATA, idx, per, shp, dd, ls = (g[k] for k in ("EV", "DATA", "idx", "per", "shp", "dd", "ls"))
def run(H=7, stop=0.30, cost=10.0, lag=0, sides=(1, -1), excl=()):
    P = {}
    for s, t, side in sorted(EV, key=lambda e: e[1]):
        if side not in sides or s in excl:
            continue
        k, _ = DATA[s]; n = s[:-4]; t = t + pd.Timedelta(hours=lag)
        cc = k.loc[t:t + pd.Timedelta(days=H)]
        if len(cc) == 0:
            continue
        adverse = cc[(cc / cc.iloc[0] - 1) * side <= -stop].index
        last = adverse[0] if len(adverse) else t + pd.Timedelta(days=H) - pd.Timedelta(hours=1)
        p = pd.Series(0.05 * side, index=k.loc[t:last].index); p.index = p.index + pd.Timedelta(hours=1); p = p.reindex(idx).fillna(0.0)
        p = p.where(k.reindex(idx - pd.Timedelta(hours=1)).notna().to_numpy(), 0.0)
        cur = P.get(n, pd.Series(0.0, index=idx)); P[n] = cur.where(cur != 0, p)
    Pdf = pd.DataFrame(P); gg = Pdf.abs().sum(axis=1); Pdf = Pdf.mul((0.5 / gg).clip(upper=1.0).fillna(1.0), axis=0)
    out = pd.Series(0.0, index=idx); contrib = {}
    for n in Pdf.columns:
        k, f = DATA[n + "USDT"]; p = Pdf[n]
        r = (k / k.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        x = p * r - p * fu - p.diff().abs().fillna(p.abs()) * cost / 1e4; out = out + x; contrib[n] = float(x.sum())
    return out, contrib
base, contrib = run()
top = sorted(contrib.items(), key=lambda kv: -kv[1])[:5]
total = sum(contrib.values())
out = {"base": per(base), "total P&L units": round(total, 3), "top 5 coins share of P&L": round(sum(v for _, v in top) / total, 2), "top 5": [[k, round(v, 3)] for k, v in top],
       "robustness": {"costs x2": per(run(cost=20.0)[0]), "one hour later": per(run(lag=1)[0]), "three hours later": per(run(lag=3)[0]),
                      "stop 20%": per(run(stop=0.20)[0]), "stop 50%": per(run(stop=0.50)[0]), "hold 5": per(run(H=5)[0]), "hold 10": per(run(H=10)[0]), "hold 14": per(run(H=14)[0]),
                      "long events only": per(run(sides=(1,))[0]), "short events only": per(run(sides=(-1,))[0]),
                      "without top 5 coins": per(run(excl=tuple(k + "USDT" for k, _ in top))[0])}}
lo = [e for e in EV if e[2] > 0]
out["long events per year"] = pd.Series([e[1].year for e in lo]).value_counts().sort_index().astype(int).to_dict()
out["long events per year"] = {str(k): int(v) for k, v in out["long events per year"].items()}
(ROOT / "results/gen429b.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

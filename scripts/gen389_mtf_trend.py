"""Gen389 (config/gen389_protocol.json). Writes results/gen389.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
s3 = open(ROOT / "scripts/gen383_ensembles.py").read().split("T = {")[0]; g3 = {"__file__": str(ROOT / "scripts/gen383_ensembles.py")}; exec(compile(s3, "g383", "exec"), g3)
CS, base, te, ke, dd, shp, per, unit, END = (g3[k] for k in ("CS", "base", "te", "ke", "dd", "shp", "per", "unit", "END"))
from qpl.lab import binance_pack as B
b384 = pd.read_parquet(ROOT / "results/gen384_basket_hourly.parquet")["basket"].reindex(base.index).fillna(0.0)
H92 = base.assign(**{"trend 4h": te, "alt kimchi": ke, "diversifier basket": b384}); v92 = unit(CS.portfolio_v5(H92)[0]); REF = (shp(v92), per(v92))
def trend_tf(rule, bars_per_day, coins=("BTC", "ETH", "SOL"), n_in=20, n_out=10, cost=5):
    out = []
    for coin in coins:
        k = B.k5(coin); c = k.close.resample(rule).last().loc[:END + " 23:00"]; h = k.high.resample(rule).max().loc[c.index]; l = k.low.resample(rule).min().loc[c.index]
        hi_in, lo_in = h.rolling(n_in).max().shift(1).to_numpy(), l.rolling(n_in).min().shift(1).to_numpy()
        hi_out, lo_out = h.rolling(n_out).max().shift(1).to_numpy(), l.rolling(n_out).min().shift(1).to_numpy()
        cv = c.to_numpy(); pos = np.zeros(len(cv)); p = 0
        for i in range(len(cv)):
            if p == 0:
                p = 1 if cv[i] > hi_in[i] else (-1 if cv[i] < lo_in[i] else 0)
            elif p == 1 and cv[i] < lo_out[i]:
                p = 0
            elif p == -1 and cv[i] > hi_out[i]:
                p = 0
            pos[i] = p
        r = c.pct_change().fillna(0); lev = (0.10 / (r.rolling(bars_per_day * 30).std().shift(1) * np.sqrt(bars_per_day * 365))).clip(upper=2.0).fillna(0)
        held = pd.Series(pos, index=c.index) * lev; held.index = held.index + pd.Timedelta(rule)
        h1 = k.close.resample("1h").last().loc[:END + " 23:00"]; r1 = h1.pct_change().fillna(0); hh = held.reindex(h1.index, method="ffill").fillna(0)
        f = B.funding(coin).copy(); f.index = f.index - pd.Timedelta(hours=1); f = f.groupby(level=0).sum().reindex(h1.index).fillna(0.0)
        out.append(hh * r1 - hh * f - hh.diff().abs().fillna(0) * cost / 1e4)
    return pd.concat(out, axis=1).fillna(0).mean(axis=1)
chk = round(float(np.corrcoef(dd(trend_tf("4h", 6).reindex(base.index).fillna(0.0)).loc["2022":], dd(base["trend 4h"]).loc["2022":])[0, 1]), 4)
t1 = trend_tf("1h", 24).reindex(base.index).fillna(0.0); t12 = trend_tf("12h", 2).reindex(base.index).fillna(0.0)
T = {"A 1h + 4h + 12h": (t1 + te + t12) / 3, "B 4h + 12h": (te + t12) / 2}
out = {"reference v9.2": [REF[0], REF[1]], "check 4h rebuild vs book trend 4h (corr)": chk, "1h alone": per(t1), "12h alone": per(t12), "4h ensemble alone": per(te), "trials": {}}
for k, t in T.items():
    b = unit(CS.portfolio_v5(H92.assign(**{"trend 4h": t}))[0]); out["trials"][k] = {"sleeve": per(t), "2022-24": shp(b, "2022", "2024"), "book": [shp(b), per(b)]}
ch = max(out["trials"], key=lambda k: out["trials"][k]["2022-24"]); r = out["trials"][ch]["book"]
out["chosen"] = ch; out["pass"] = bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))
(ROOT / "results/gen389.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

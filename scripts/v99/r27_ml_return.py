"""v9.9 R27 (research/v99/r27_protocol.json): random forest and a small neural net in place of the ridge in the ridge ML sleeve.
Writes results/v99/r27_ml_return.json."""
import json
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import ridge_live as RL
warnings.filterwarnings("ignore")
FLAGS = dict(kb=True, volscale=True, spot=True, vrp=True, cal=True)


def sleeve(make, idx):
    orig = RL.Ridge; RL.Ridge = lambda alpha=10.0: make()
    try:
        w = RL.ridge_weights(**FLAGS)
    finally:
        RL.Ridge = orig
    return CS._from_daily_weights(w, list(w.columns), 5).reindex(idx).fillna(0.0), w


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    ref = book(V8); r0, w0 = sleeve(lambda: RL.Ridge(alpha=10.0) if False else __import__("sklearn.linear_model", fromlist=["Ridge"]).Ridge(alpha=10.0), idx)
    out = {"reference v9.8": ref, "corr(rebuilt ridge, v9.8 ridge ML) daily": round(float(dd(r0).corr(dd(V8["ridge ML"]))), 3), "rebuilt ridge sleeve": per(r0)}
    for name, make in (("A random forest", lambda: RandomForestRegressor(n_estimators=300, max_depth=4, min_samples_leaf=50, max_features=0.5, random_state=0, n_jobs=-1)),
                       ("B neural network", lambda: MLPRegressor(hidden_layer_sizes=(16,), alpha=1.0, early_stopping=True, max_iter=500, random_state=0))):
        r1, w1 = sleeve(make, idx)
        b = book(V8.assign(**{"ridge ML": V8["ridge ML"] + r1 - r0}))
        out[name] = {"sleeve 2022 / 23-24 / 25-26": per(r1), "corr with ridge weights": round(float(w1.stack().corr(w0.stack())), 3), "book": b,
                     "pass": bool(b[0] >= ref[0] + 0.05 and all(b[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    (ROOT / "results/v99/r27_ml_return.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

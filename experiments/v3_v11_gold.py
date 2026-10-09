"""V11 gold: neighbourhood + costs on TRAIN+VALIDATION, then (stage 'oos') a single frozen OOS look."""
from __future__ import annotations
import itertools, json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A
from qpl.instruments import get
from qpl.research import factory as F, pipeline as P
from qpl.statistics import tests as T
from qpl.strategies import v3_intraday  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
NAN = float("nan")
hyp = F.Hypothesis("V11_ASIAN_BREAKOUT", "", "", "", "", "", "", "", "")
stage = sys.argv[1]
ctx = P.context("dukascopy", "XAUUSD", "M15", 180, 660); days = P.trading_days(ctx); inst = get("MGC")
DEVP = ("2013-01-01", "2020-12-31")
def run(prm, cm=1.0):
    u = P.usd(P.backtest("asian_breakout", ctx, prm, inst), inst, contracts=1, cost_mult=cm, slip_mult=cm)
    return u, A.daily_pnl(u, days)["pnl"]
sh = lambda x: float(x.mean() / x.std() * np.sqrt(252))
FROZEN = dict(asia_start=1140, asia_end=180, exit_min=660, stop_frac=NAN)
out = {}
if stage == "dev":
    rows = []
    for a0, a1, x, s in itertools.product([1080, 1140, 1200], [120, 180, 240], [540, 600, 660, 720], [NAN, 1.0]):
        prm = dict(asia_start=a0, asia_end=a1, exit_min=x, stop_frac=s)
        u, d = run(prm)
        rows.append({**prm, "train": sh(d.loc[P.SPLITS["train"][0]:P.SPLITS["train"][1]]), "val": sh(d.loc[P.SPLITS["validation"][0]:P.SPLITS["validation"][1]])})
    nb = pd.DataFrame(rows)
    nb.to_csv(ROOT / "results" / "v3_v11_neighbours.csv", index=False)
    u, d = run(FROZEN); u2, d2 = run(FROZEN, 2.0); u3, d3 = run(FROZEN, 3.0)
    out = {"n_neighbours": len(nb), "frac_train_pos": float((nb.train > 0).mean()), "frac_val_pos": float((nb.val > 0).mean()),
           "frac_both_pos": float(((nb.train > 0) & (nb.val > 0)).mean()), "median_train": float(nb.train.median()), "median_val": float(nb.val.median()),
           "frozen": {"train": sh(d.loc["2013":"2018"]), "val": sh(d.loc["2019":"2020"]), "dev_2x": sh(d2.loc[DEVP[0]:DEVP[1]]), "dev_3x": sh(d3.loc[DEVP[0]:DEVP[1]]),
                      "dev_trades": int(((u.day >= DEVP[0]) & (u.day <= DEVP[1])).sum()), "by_year": {int(k): float(v) for k, v in d.loc[DEVP[0]:DEVP[1]].groupby(d.loc[DEVP[0]:DEVP[1]].index.year).sum().items()},
                      "long_share": float((u.dir > 0).mean())}}
elif stage == "oos":
    u, d = run(FROZEN); u3, d3 = run(FROZEN, 3.0)
    x = d.loc[P.SPLITS["oos"][0]:P.SPLITS["oos"][1]]
    out = {"oos_sharpe": sh(x), "oos_total": float(x.sum()), "oos_trades": int(((u.day >= P.SPLITS["oos"][0])).sum()),
           "oos_3x": sh(d3.loc[P.SPLITS["oos"][0]:P.SPLITS["oos"][1]]), "nw": T.newey_west_t(x.to_numpy()),
           "by_year": {int(k): float(v) for k, v in x.groupby(x.index.year).sum().items()}}
(ROOT / "results" / f"v3_v11_{stage}.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "experiment", "hypothesis_id": "V11_ASIAN_BREAKOUT", "instrument": "MGC", "stage": f"v11_{stage}", "frozen": {k: (None if v != v else v) for k, v in FROZEN.items()}, "summary": out})
print(json.dumps(out, indent=1, default=float))

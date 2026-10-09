"""Phase 7: Probability of Backtest Overfitting (Bailey, Borwein, Lopez de Prado & Zhu 2017, CSCV)
for (a) the H3 parameter grid and (b) the whole gen-1/2 NQ intraday search universe."""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A  # noqa: E402
from qpl.instruments import get  # noqa: E402
from qpl.research import factory as F, pipeline as P  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen1_screen import GRIDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def cscv_pbo(Mx: np.ndarray, S: int = 16) -> dict:
    T, N = Mx.shape
    blocks = np.array_split(np.arange(T), S)
    lam, perf_oos_best, perf_is_best = [], [], []
    for combo in itertools.combinations(range(S), S // 2):
        is_idx = np.concatenate([blocks[i] for i in combo])
        oos_idx = np.concatenate([blocks[i] for i in range(S) if i not in combo])
        a, b = Mx[is_idx], Mx[oos_idx]
        sa = a.mean(0) / (a.std(0) + 1e-12); sb = b.mean(0) / (b.std(0) + 1e-12)
        n_star = int(np.argmax(sa))
        w = (np.argsort(np.argsort(sb))[n_star] + 1) / (N + 1)        # relative OOS rank of the IS winner
        lam.append(np.log(w / (1 - w)))
        perf_is_best.append(sa[n_star] * np.sqrt(252)); perf_oos_best.append(sb[n_star] * np.sqrt(252))
    lam = np.array(lam)
    slope = np.polyfit(perf_is_best, perf_oos_best, 1)[0]
    return {"pbo": float(np.mean(lam < 0)), "n_combinations": len(lam), "N_variants": N, "T_days": T,
            "median_oos_sharpe_of_is_winner": float(np.median(perf_oos_best)),
            "p_oos_loss_of_is_winner": float(np.mean(np.array(perf_oos_best) < 0)),
            "is_oos_degradation_slope": float(slope)}


def daily_matrix(variants, proxy="US100", fut="NQ"):
    ctx = P.context("dukascopy", proxy, "M15"); days = P.trading_days(ctx); inst = get(fut)
    cols = {}
    for name, strat, prm in variants:
        u = P.usd(P.backtest(strat, ctx, prm, inst), inst, contracts=1)
        cols[name] = A.daily_pnl(u, days)["pnl"]
    D = pd.DataFrame(cols).loc["2013-09-01":"2023-09-11"]
    return D


h3grid = [(f"h3_lb{lb}_m{m}_c{c}", "noise_area", dict(lookback=lb, mult=m, trail="band_mean", check_min=c))
          for lb in (10, 14, 20) for m in (0.75, 1.0, 1.25, 1.5) for c in (30, 60)]
universe = [(f"{hid}_{i}", strat, prm) for hid, (strat, grid) in GRIDS.items() for i, prm in enumerate(grid)]
out = {}
D1 = daily_matrix(h3grid)
out["h3_grid"] = cscv_pbo(D1.to_numpy())
D2 = daily_matrix(universe + h3grid)
out["nq_search_universe"] = cscv_pbo(D2.to_numpy())
out["nq_search_universe"]["note"] = "gen-1/2 grids (ORB, IM, noise-area, overnight, gap-fade) + H3 neighbourhood on the NQ proxy"
(ROOT / "results" / "v3_pbo.json").write_text(json.dumps(out, indent=1))
F.append({"kind": "experiment", "hypothesis_id": "PBO", "summary": out})
print(json.dumps(out, indent=1))

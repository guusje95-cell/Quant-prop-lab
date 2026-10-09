"""Pre-registered single-use cross-market holdout for H3 (config/holdout_v3_protocol.json)."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A
from qpl.instruments import get
from qpl.research import pipeline as P, factory as F
from qpl.statistics import tests as T

ROOT = Path(__file__).resolve().parents[1]
FROZEN = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60, cat_stop_sd=1.5, max_trades=6)
out = {"B": {}, "A": {}}
dB = {}
for sym in ("ES", "YM", "RTY"):
    inst = get(sym)
    ctx = P.context("topstepx", sym, "1h", 540, 960); days = P.trading_days(ctx)
    tr = P.backtest("noise_area", ctx, FROZEN, inst)
    u = P.usd(tr, inst, contracts=1, norm=False)
    m = P.split_metrics(u, days, {"B": ("2025-03-21", "2026-04-15")})["B"]
    u2 = P.usd(tr, inst, contracts=1, cost_mult=2, slip_mult=2, norm=False)
    m2 = P.split_metrics(u2, days, {"B": ("2025-03-21", "2026-04-15")})["B"]
    d = A.daily_pnl(u, days)["pnl"].loc["2025-03-21":"2026-04-15"]
    dB[sym] = d
    out["B"][sym] = {"sharpe": m["sharpe"], "total": m["total_usd"], "trades": m.get("trades"), "max_dd": m["max_dd_usd"],
                     "sharpe_2x_cost": m2["sharpe"], "nw": T.newey_west_t(d.to_numpy())}
    ctx = P.context("topstepx", sym, "15min"); days = P.trading_days(ctx)
    u = P.usd(P.backtest("noise_area", ctx, FROZEN, inst), inst, contracts=1, norm=False)
    m = P.split_metrics(u, days, {"A": ("2026-01-20", "2026-04-15")})["A"]
    out["A"][sym] = {"sharpe": m["sharpe"], "total": m["total_usd"], "trades": m.get("trades")}
D = pd.DataFrame(dB).fillna(0)
pooled = (D / D.std()).mean(1)
out["pooled_B_sharpe"] = float(pooled.mean() / pooled.std() * np.sqrt(252))
out["pooled_B_nw"] = T.newey_west_t(pooled.to_numpy())
out["corr_B"] = D.corr().round(3).to_dict()
out["verdict"] = "SUPPORT" if out["pooled_B_sharpe"] > 0 else "NO_SUPPORT (downgrade H3 to EXPLORATORY)"
(ROOT / "results" / "v3_holdout_crossmarket.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "holdout_evaluation", "protocol": "config/holdout_v3_protocol.json", "result": out})
print(json.dumps(out, indent=1, default=float))

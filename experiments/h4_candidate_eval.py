"""Full robustness evaluation of the frozen H4 (overnight drift) specification.

FROZEN SPEC (committed before looking at OOS 2021-01..2023-09):
  long at 19:00 ET (bar open), exit at the close of the bar ending 03:00 ET,
  protective stop 1.0 x ATR14 (daily RTH ATR, known at the prior close),
  every CME session whose trading date is a NYSE trading day (Sun-Thu evenings).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A  # noqa: E402
from qpl.instruments import get  # noqa: E402
from qpl.research import pipeline as P  # noqa: E402
from qpl.research import registry as R  # noqa: E402
from qpl.robustness import suite as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FROZEN = dict(entry_min=19 * 60, exit_min=3 * 60, stop_atr=1.0)
MARKETS = {"NQ": "US100", "ES": "US500", "YM": "US30"}
DEV = (P.SPLITS["train"][0], P.SPLITS["validation"][1])
OOS = P.SPLITS["oos"]


def random_window_control(ctx, inst, hours=8, cost_pts=None, period=DEV):
    """Sharpe of a long position over every alternative 8h window (start on each hour),
    same cost per trade -> where does the frozen window rank?"""
    c = ctx["close"]
    r = np.log(c).diff()
    dt = ctx.index.to_series().diff().dt.total_seconds().to_numpy() / 60
    r[dt > 120] = 0.0       # never span the daily break / data holes
    m = (ctx.index >= period[0]) & (ctx.index <= period[1] + " 23:59")
    r = r[m]
    et_h = (ctx["et_min"][m] // 60).to_numpy()
    d = pd.DatetimeIndex(ctx["cme_date"][m])
    px = c[m].to_numpy()
    out = {}
    cost_frac = cost_pts / P.REF_PRICE[inst.symbol]
    for start in range(24):
        hrs = [(start + k) % 24 for k in range(hours)]
        sel = np.isin(et_h, hrs)
        # group by the date of the window START (windows crossing midnight belong to one block)
        key = d.to_numpy() if start >= 18 or start + hours <= 24 else d.to_numpy()
        s = pd.Series(np.where(sel, r.to_numpy(), 0.0)).groupby(key).sum() - cost_frac
        out[start] = float(s.mean() / s.std() * np.sqrt(252))
    return out


def main():
    res = {"frozen_spec": FROZEN, "markets": {}}
    dailies_dev, dailies_oos = {}, {}
    for fut, proxy in MARKETS.items():
        ctx = P.context("dukascopy", proxy, "M15")
        days = P.trading_days(ctx)
        inst = get(fut)
        tr = P.backtest("overnight_drift", ctx, FROZEN, inst)
        u = P.usd(tr, inst, contracts=1)
        sm = P.split_metrics(u, days, {**P.SPLITS, "dev": DEV})
        dly = A.daily_pnl(u, days)
        dailies_dev[fut] = dly.loc[DEV[0]:DEV[1], "pnl"]
        dailies_oos[fut] = dly.loc[OOS[0]:OOS[1], "pnl"]
        r = {"splits": sm}
        r["cost_stress_dev"] = S.cost_stress(tr, inst, days, DEV).to_dict("records")
        r["cost_stress_oos"] = S.cost_stress(tr, inst, days, OOS).to_dict("records")
        nb = S.neighbors("overnight_drift", ctx, FROZEN, {"entry_min": [1080, 1140, 1200, 1260],
                                                          "exit_min": [120, 150, 180, 210, 240],
                                                          "stop_atr": [0.75, 1.0, 1.5, np.nan]}, inst, days, DEV)
        r["neighbors_dev"] = {"n": len(nb), "sharpe_min": nb.sharpe.min(), "sharpe_median": nb.sharpe.median(),
                              "sharpe_max": nb.sharpe.max(), "frac_positive": float((nb.sharpe > 0).mean()),
                              "frozen_rank_pct": float((nb.sharpe < sm["dev"]["sharpe"]).mean())}
        nb.to_csv(ROOT / "results" / f"h4_neighbors_{fut}.csv", index=False)
        rc = ctx.groupby("date")["close"].last()
        rc.index = pd.DatetimeIndex(rc.index)
        r["regimes_all"] = S.regimes(dly["pnl"].loc[DEV[0]:OOS[1]], rc)
        cost_pts = inst.cost_per_rt() / inst.point_value
        r["random_window_control_dev"] = random_window_control(ctx, inst, cost_pts=cost_pts)
        grid = [dict(entry_min=a, exit_min=b, stop_atr=1.0) for a in (1080, 1140, 1200, 1260, 0)
                for b in (120, 180, 240, 300)]
        wf = S.walk_forward("overnight_drift", ctx, grid, inst, days, DEV[0], OOS[1], train_years=3)
        r["walk_forward"] = {k: v for k, v in wf.items() if k not in ("oos_daily", "all_variants_daily")}
        n_trials = R.count()
        r["stats_dev"] = S.stat_validation(dailies_dev[fut], n_trials, wf["all_variants_daily"].loc[DEV[0]:DEV[1]])
        r["stats_oos"] = S.stat_validation(dailies_oos[fut], 1)
        r["mc_dev"] = S.mc_paths(dailies_dev[fut].to_numpy(), horizon=252)
        r["trade_shuffle_dd_dev"] = S.trade_shuffle_dd(u[(u.day >= DEV[0]) & (u.day <= DEV[1])]["pnl_usd"].to_numpy())
        res["markets"][fut] = r
        R.record(generation=3, family="H4_OVERNIGHT", hypothesis_id="H4_OVERNIGHT", strategy="overnight_drift",
                 instrument=fut, data_source=f"dukascopy:{proxy}", timeframe="M15", params=FROZEN,
                 stage="frozen_full_eval", period="train+validation+oos", train_period=str(P.SPLITS["train"]),
                 validation_period=str(P.SPLITS["validation"]), oos_period=str(OOS),
                 metrics={k: v for k, v in sm.items()}, stats={"dev": r["stats_dev"], "oos": r["stats_oos"]},
                 decision="evaluate", reason="frozen H4 spec full evaluation")
    # portfolio of the three markets (1 contract each) and correlation
    Ddev = pd.DataFrame(dailies_dev)
    Doos = pd.DataFrame(dailies_oos)
    res["corr_dev"] = Ddev.corr().round(3).to_dict()
    res["corr_oos"] = Doos.corr().round(3).to_dict()
    (ROOT / "results" / "h4_candidate_eval.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    res = main()
    for fut, r in res["markets"].items():
        sp = r["splits"]
        print(fut, {k: (round(v["sharpe"], 2), round(v["total_usd"]), v.get("trades"), round(v["max_dd_usd"])) for k, v in sp.items()})
        print("  cost stress OOS:", [(x["scenario"], round(x["sharpe"], 2)) for x in r["cost_stress_oos"]])
        print("  neighbors:", {k: round(v, 2) for k, v in r["neighbors_dev"].items()})
        print("  WF:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r["walk_forward"].items() if k != "picks"})
        print("  WF picks:", [(p["test_year"], p["pick"]["entry_min"], p["pick"]["exit_min"], round(p["oos_sharpe"], 2)) for p in r["walk_forward"]["picks"]])
        print("  stats dev:", {k: v for k, v in r["stats_dev"].items()})
        print("  stats oos:", {k: v for k, v in r["stats_oos"].items()})
        print("  yearly:", {k: round(v["total"]) for k, v in r["regimes_all"]["yearly"].items()})
        print("  trend:", {k: round(v["sharpe"], 2) for k, v in r["regimes_all"]["trend"].items()},
              "vol:", {k: round(v["sharpe"], 2) for k, v in r["regimes_all"]["vol"].items()})
        print("  crises:", {k: round(v) for k, v in r["regimes_all"]["crises"].items()})
        rw = r["random_window_control_dev"]
        print("  random-window Sharpe by start hour:", {k: round(v, 2) for k, v in rw.items()})
    print("corr dev", res["corr_dev"]); print("corr oos", res["corr_oos"])

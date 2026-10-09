"""Generic full evaluation of a frozen candidate (one call = one OOS 'look', recorded)."""
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
DEV = (P.SPLITS["train"][0], P.SPLITS["validation"][1])
OOS = P.SPLITS["oos"]


def evaluate(name: str, hid: str, strategy: str, frozen: dict, markets: dict, nb_grid: dict, wf_grid: list,
             gen: int, tf: str = "M15", source: str = "dukascopy", freeze_ts: str | None = None) -> dict:
    """freeze_ts pins the multiple-testing trial count (audit fix A-R1: DSR drifted with ledger size)."""
    n_trials = R.unique_variants(freeze_ts)
    res = {"frozen_spec": frozen, "markets": {}, "n_trials_pinned": n_trials, "freeze_ts": freeze_ts}
    dd, do = {}, {}
    for fut, proxy in markets.items():
        ctx = P.context(source, proxy, tf)
        days = P.trading_days(ctx)
        inst = get(fut)
        tr = P.backtest(strategy, ctx, frozen, inst)
        u = P.usd(tr, inst, contracts=1)
        sm = P.split_metrics(u, days, {**P.SPLITS, "dev": DEV})
        dly = A.daily_pnl(u, days)
        dd[fut] = dly.loc[DEV[0]:DEV[1], "pnl"]
        do[fut] = dly.loc[OOS[0]:OOS[1], "pnl"]
        r = {"splits": sm,
             "cost_stress_dev": S.cost_stress(tr, inst, days, DEV).to_dict("records"),
             "cost_stress_oos": S.cost_stress(tr, inst, days, OOS).to_dict("records")}
        nb = S.neighbors(strategy, ctx, frozen, nb_grid, inst, days, DEV)
        nb.to_csv(ROOT / "results" / f"{name}_neighbors_{fut}.csv", index=False)
        r["neighbors_dev"] = {"n": len(nb), "sharpe_min": nb.sharpe.min(), "sharpe_median": nb.sharpe.median(),
                              "sharpe_max": nb.sharpe.max(), "frac_positive": float((nb.sharpe > 0).mean())}
        rc = ctx.groupby("date")["close"].last()
        rc.index = pd.DatetimeIndex(rc.index)
        r["regimes_all"] = S.regimes(dly["pnl"].loc[DEV[0]:OOS[1]], rc)
        wf = S.walk_forward(strategy, ctx, wf_grid, inst, days, DEV[0], OOS[1], train_years=3)
        r["walk_forward"] = {k: v for k, v in wf.items() if k not in ("oos_daily", "all_variants_daily")}
        r["stats_dev"] = S.stat_validation(dd[fut], n_trials, wf["all_variants_daily"].loc[DEV[0]:DEV[1]])
        r["stats_oos"] = S.stat_validation(do[fut], 1)
        r["mc_dev"] = S.mc_paths(dd[fut].to_numpy(), horizon=252)
        res["markets"][fut] = r
        R.record(generation=gen, family=hid, hypothesis_id=hid, strategy=strategy, instrument=fut,
                 data_source=f"{source}:{proxy}", timeframe=tf, params=frozen, stage="frozen_full_eval",
                 period="train+validation+oos", train_period=str(P.SPLITS["train"]),
                 validation_period=str(P.SPLITS["validation"]), oos_period=str(OOS), metrics=sm,
                 stats={"dev": r["stats_dev"], "oos": r["stats_oos"]}, decision="evaluate",
                 reason=f"{name} frozen full evaluation (single OOS look)")
    res["corr_dev"] = pd.DataFrame(dd).corr().round(3).to_dict()
    res["corr_oos"] = pd.DataFrame(do).corr().round(3).to_dict()
    (ROOT / "results" / f"{name}_eval.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def report(res: dict) -> None:
    for fut, r in res["markets"].items():
        sp = r["splits"]
        print(fut, {k: (round(v["sharpe"], 2), round(v["total_usd"]), v.get("trades"), round(v["max_dd_usd"])) for k, v in sp.items()})
        print("  cost stress OOS:", [(x["scenario"], round(x["sharpe"], 2)) for x in r["cost_stress_oos"]])
        print("  neighbors:", {k: round(v, 2) for k, v in r["neighbors_dev"].items()})
        print("  WF:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r["walk_forward"].items() if k != "picks"})
        print("  stats dev: nw_t %.2f psr %.3f dsr %.3f rc_p %s" % (r["stats_dev"]["nw_t"], r["stats_dev"]["psr_vs0"],
              r["stats_dev"]["dsr"], r["stats_dev"].get("reality_check", {}).get("rc_pvalue")))
        print("  stats oos: nw_t %.2f p %.3f sharpe_ci %s" % (r["stats_oos"]["nw_t"], r["stats_oos"]["nw_p_one_sided"],
              tuple(round(x, 2) for x in r["stats_oos"]["sharpe_ci95"])))
        print("  yearly:", {k: round(v["total"]) for k, v in r["regimes_all"]["yearly"].items()})
        print("  trend:", {k: round(v["sharpe"], 2) for k, v in r["regimes_all"]["trend"].items()},
              "vol:", {k: round(v["sharpe"], 2) for k, v in r["regimes_all"]["vol"].items()})
        print("  crises:", {k: round(v) for k, v in r["regimes_all"]["crises"].items()})
    print("corr dev", res["corr_dev"]); print("corr oos", res["corr_oos"])


if __name__ == "__main__":
    which = sys.argv[1]
    if which == "h3":
        frozen = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
        res = evaluate("h3", "H3_NOISE", "noise_area", frozen, {"NQ": "US100", "ES": "US500", "YM": "US30"},
                       {"lookback": [10, 14, 20], "mult": [1.0, 1.25, 1.5], "check_min": [30, 60]},
                       [dict(lookback=lb, mult=m, trail="band_mean", check_min=c) for lb in (10, 14, 20)
                        for m in (0.75, 1.0, 1.25, 1.5) for c in (30, 60)], gen=3, freeze_ts="2026-10-08T21:24:43")
        report(res)

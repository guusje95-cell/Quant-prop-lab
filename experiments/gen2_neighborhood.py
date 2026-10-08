"""Generation 2: parameter neighborhoods on TRAIN and VALIDATION (deployment-normalized costs)
for the three families surviving gen-1/2 screening. OOS remains untouched."""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.instruments import get  # noqa: E402
from qpl.research import pipeline as P  # noqa: E402
from qpl.research import registry as R  # noqa: E402

NAN = float("nan")
SPL = {"train": P.SPLITS["train"], "validation": P.SPLITS["validation"]}
GRIDS = {
    "H3_NOISE": ("noise_area", [dict(lookback=lb, mult=m, trail="band_mean", check_min=c)
                                for lb, m, c in itertools.product([10, 14, 20], [0.75, 1.0, 1.25, 1.5], [30, 60])]),
    "H4_OVERNIGHT": ("overnight_drift", [dict(entry_min=a, exit_min=b, stop_atr=s)
                                         for a, b, s in itertools.product([1080, 1140, 1200, 1320, 0],
                                                                          [180, 240, 300, 360], [NAN, 1.0])]),
    "H2_IM": ("intraday_momentum", [dict(thr_sd=th, use_r12=u, signal_end_min=se)
                                    for th, u, se in itertools.product([0.0, 0.15, 0.25, 0.35], [False, True], [600, 630])]),
}
MARKETS = {"ES": "US500", "NQ": "US100", "YM": "US30"}


def run(hids=None):
    rows = []
    for hid, (strat, grid) in GRIDS.items():
        if hids and hid not in hids:
            continue
        for fut, proxy in MARKETS.items():
            ctx = P.context("dukascopy", proxy, "M15")
            days = P.trading_days(ctx)
            inst = get(fut)
            for prm in grid:
                tr = P.backtest(strat, ctx, prm, inst)
                u = P.usd(tr, inst, contracts=1)
                sm = P.split_metrics(u, days, SPL)
                tv = P.split_metrics(u, days, {"tv": (SPL["train"][0], SPL["validation"][1])})["tv"]
                for s, mm in sm.items():
                    R.record(generation=2, family=hid, hypothesis_id=hid, strategy=strat, instrument=fut,
                             data_source=f"dukascopy:{proxy}", timeframe="M15", params=prm, stage=f"neighborhood_norm_{s}",
                             period=s, metrics=mm, decision="info", reason="gen2 neighborhood, normalized costs")
                rows.append(dict(hid=hid, mkt=fut, prm=json.dumps(prm), tr_sh=sm["train"]["sharpe"],
                                 va_sh=sm["validation"]["sharpe"], tv_sh=tv["sharpe"], tv_n=tv.get("trades", 0),
                                 tv_exp=tv.get("expectancy_usd", np.nan), tv_pf=tv.get("profit_factor", np.nan),
                                 tv_dd=tv["max_dd_usd"]))
    df = pd.DataFrame(rows)
    df.to_csv(Path(__file__).resolve().parents[1] / "results" / "gen2_neighborhood.csv", index=False)
    return df


if __name__ == "__main__":
    df = run()
    pd.set_option("display.width", 250, "display.max_rows", 500, "display.max_colwidth", 90)
    print(df.groupby(["hid", "mkt"])[["tr_sh", "va_sh", "tv_sh"]].agg(["mean", "median", "min", "max"]).round(2))
    for hid in df.hid.unique():
        print(df[df.hid == hid].sort_values("tv_sh", ascending=False).head(15).round(2).to_string())

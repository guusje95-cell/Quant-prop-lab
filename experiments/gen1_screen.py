"""Generation 1 screening: predefined modest grids, TRAIN period only, 3 index markets.
Every variant is recorded in the experiment database."""
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
from qpl.research.hypotheses import GEN1  # noqa: E402

NAN = float("nan")
GRIDS = {
    "H1_ORB": ("orb", [dict(or_bars=k, mode=m, stop=s, tgt_R=t) for k, m, s, t in itertools.product(
        [1, 2, 4], ["candle_mkt", "bracket"], ["or", 0.5], [NAN, 2.0])]),
    "H2_IM": ("intraday_momentum", [dict(thr_sd=th, use_r12=u, signal_end_min=se) for th, u, se in itertools.product(
        [0.0, 0.25], [False, True], [600, 630])]),
    "H3_NOISE": ("noise_area", [dict(mult=m, trail=tr, check_min=c) for m, tr, c in itertools.product(
        [0.75, 1.0, 1.25], ["band", "band_mean"], [15, 30])]),
    "H4_OVERNIGHT": ("overnight_drift", [dict(entry_min=a, exit_min=b, stop_atr=s) for (a, b), s in itertools.product(
        [(1080, 240), (1080, 570), (1200, 240), (1200, 570), (0, 240), (120, 240), (0, 570)], [NAN, 1.0])]),
    "H5_GAPFADE": ("gap_fade", [dict(gap_min_atr=g, stop_atr=s, exit_min=x) for g, s, x in itertools.product(
        [0.2, 0.4], [0.5, 1.0], [720, 960])]),
}
MARKETS = {"ES": "US500", "NQ": "US100", "YM": "US30"}


def main(gen: int = 1, norm: bool = False, tag: str = "gen1_screen"):
    rows = []
    for hid, doc in GEN1.items():
        R.register_hypothesis(hid, doc["family"], gen, doc)
    for hid, (strat, grid) in GRIDS.items():
        for fut, proxy in MARKETS.items():
            ctx = P.context("dukascopy", proxy, "M15")
            days = P.trading_days(ctx)
            inst = get(fut)
            for prm in grid:
                tr = P.backtest(strat, ctx, prm, inst)
                u = P.usd(tr, inst, contracts=1, norm=norm)
                g = P.usd(tr, inst, contracts=1, cost_mult=0.0, slip_mult=0.0, norm=norm)   # gross reference
                m = P.split_metrics(u, days, {"train": P.SPLITS["train"]})["train"]
                mg = P.split_metrics(g, days, {"train": P.SPLITS["train"]})["train"]
                d = P.daily(u, days, *P.SPLITS["train"])
                yrs = d["pnl"].groupby(d.index.year).sum()
                m["pct_years_positive"] = float((yrs > 0).mean())
                m["gross_sharpe"] = mg["sharpe"]
                m["gross_expectancy"] = mg.get("expectancy_usd", np.nan)
                ok = (m["sharpe"] > 0.5 and m.get("trades", 0) >= 100 and m.get("profit_factor", 0) > 1.1
                      and m["pct_years_positive"] >= 0.6)
                R.record(generation=gen, family=GEN1[hid]["family"], hypothesis_id=hid, strategy=strat,
                         instrument=fut, data_source=f"dukascopy:{proxy}", timeframe="M15", params=prm,
                         stage="screen_train" + ("_norm" if norm else "_histcost"), period="train", train_period=str(P.SPLITS["train"]),
                         metrics=m, decision="pass" if ok else "reject",
                         reason="screen: sharpe>0.5, trades>=100, PF>1.1, >=60% years positive")
                rows.append({"hid": hid, "mkt": fut, "prm": json.dumps(prm), "sh": m["sharpe"], "gsh": m["gross_sharpe"],
                             "exp": m.get("expectancy_usd"), "gexp": m["gross_expectancy"], "n": m.get("trades"),
                             "pf": m.get("profit_factor"), "yrs+": m["pct_years_positive"], "pass": ok})
    df = pd.DataFrame(rows)
    out = Path(__file__).resolve().parents[1] / "results" / f"{tag}.csv"
    df.to_csv(out, index=False)
    return df


if __name__ == "__main__":
    norm = "--norm" in sys.argv
    df = main(gen=2 if norm else 1, norm=norm, tag="gen2_screen_norm" if norm else "gen1_screen")
    pd.set_option("display.width", 250, "display.max_rows", 500, "display.max_colwidth", 80)
    print(df.groupby("hid")[["sh", "gsh", "pass"]].agg(["mean", "max"]))
    print(df.sort_values("sh", ascending=False).head(40).to_string())

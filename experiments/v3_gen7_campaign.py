"""v3 generation 7: broad discovery. Pre-registered hypotheses, TRAIN + VALIDATION only.
Usage: python experiments/v3_gen7_campaign.py"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.research import factory as F  # noqa: E402
from qpl.strategies import v3_intraday  # noqa: E402,F401

ROOT = Path(__file__).resolve().parents[1]
NAN = float("nan")
MKTS = {"NQ": "US100", "ES": "US500", "YM": "US30"}

HYPS = {
    "V1_FAILED_BREAKOUT": (F.Hypothesis(
        "V1_FAILED_BREAKOUT", "mean reversion/failed breakout",
        "A push through the prior-day RTH high (low) that closes back inside within 1-2 bars reverts toward the session mean.",
        "Stop-runs above obvious reference levels exhaust liquidity-taking flow; trapped breakout traders exit.",
        "TRAIN net Sharpe < 0.5 in every market/variant, or no better than the opposite (breakout-continuation) direction.",
        "15m index bars + prior-day RTH high/low", "back_bars {1,2} x max_trades {1,2}", "zero (flat) and H3 momentum",
        "config/promotion_criteria.json"), "failed_breakout",
        [dict(back_bars=b, max_trades=m) for b, m in itertools.product([1, 2], [1, 2])]),
    "V2_EXTREME_REVERSION": (F.Hypothesis(
        "V2_EXTREME_REVERSION", "mean reversion/extreme move",
        "A 15-minute return beyond k time-of-day sigmas partially reverses over the next hour.",
        "Liquidity shocks (large market orders) overshoot; liquidity providers are compensated for absorbing them.",
        "TRAIN net Sharpe < 0.5 for all k/hold variants.", "15m index bars", "k {2.5,3.5} x hold {2,4} bars",
        "zero", "config/promotion_criteria.json"), "extreme_reversion",
        [dict(k=k, hold_bars=h) for k, h in itertools.product([2.5, 3.5], [2, 4])]),
    "V3_COMPRESSION_BREAKOUT": (F.Hypothesis(
        "V3_COMPRESSION_BREAKOUT", "volatility/compression-expansion",
        "After a compressed day (prior range <= 0.6-0.8 of its 20-day average), the opening-range breakout is more likely to follow through.",
        "Volatility clustering and range expansion after contraction (Crabel; vol mean-reversion).",
        "Compressed-day breakout no better than the same breakout on non-compressed days (baseline) or TRAIN Sharpe < 0.5.",
        "15m bars, prior-day range", "range_ratio_max {0.6,0.8} x tgt_R {nan,2}", "invert=True (non-compressed days)",
        "config/promotion_criteria.json"), "compression_breakout",
        [dict(or_bars=2, range_ratio_max=r, tgt_R=t, invert=i) for r, t, i in itertools.product([0.6, 0.8], [NAN, 2.0], [False, True])]),
    "V4_TURN_OF_MONTH": (F.Hypothesis(
        "V4_TURN_OF_MONTH", "calendar",
        "US index futures earn higher RTH returns on the last trading day and first 3 trading days of the month.",
        "Month-end pension/payroll flows and portfolio rebalancing (Lakonishok & Smidt 1988; Ariel 1987; McConnell & Xu 2008).",
        "TOM RTH long not better than non-TOM RTH long (baseline) or TRAIN Sharpe < 0.5.",
        "15m bars + exchange calendar", "window (-1,3); invert baseline", "invert=True (non-TOM days)",
        "config/promotion_criteria.json",
        sources=[{"title": "McConnell & Xu (2008) Equity Returns at the Turn of the Month", "url": "https://doi.org/10.2469/faj.v64.n2.11",
                  "published": "2008", "sample": "US 1926-2005", "limitations": "close-to-close, not intraday; pre-2006 sample"}]),
        "turn_of_month", [dict(window=(-1, 3), invert=i) for i in (False, True)]),
    "V9_GAP_CONTINUATION": (F.Hypothesis(
        "V9_GAP_CONTINUATION", "session/gap", "EXPLORATORY sign-reversal of rejected H5: moderate opening gaps continue intraday.",
        "Overnight information keeps being incorporated after the open.", "TRAIN net Sharpe < 0.5. Penalized: hypothesis formed after observing H5.",
        "15m bars", "gap_min {0.2,0.4}", "zero", "config/promotion_criteria.json"), "gap_continuation",
        [dict(gap_min_atr=g, stop_atr=0.5) for g in (0.2, 0.4)]),
    "V10_NOISE_PULLBACK": (F.Hypothesis(
        "V10_NOISE_PULLBACK", "momentum/pullback entry (H3 refinement)",
        "Entering H3 breakouts on a pullback to the session TWAP (limit order) improves net expectancy vs market entry.",
        "Better entry price and fewer false breakouts (unfilled limit = filtered signal).",
        "Net Sharpe not above H3 baseline on TRAIN+VALIDATION.", "15m bars", "wait_bars {4,8}", "H3 frozen spec",
        "config/promotion_criteria.json"), "noise_pullback",
        [dict(lookback=14, mult=1.25, trail="band_mean", check_min=60, wait_bars=w) for w in (4, 8)]),
}


def main():
    rows = []
    for hid, (hyp, strat, grid) in HYPS.items():
        hyp.register()
        for fut, proxy in MKTS.items():
            for prm in grid:
                rec = F.evaluate_variant(hyp, strat, fut, proxy, prm, stage="gen7_screen")
                tr, va = rec["periods"]["train"], rec["periods"]["validation"]
                rows.append(dict(hid=hid, mkt=fut, prm=json.dumps(prm), tr_sh=tr["net"]["sharpe"], tr_gross=tr["gross_sharpe"],
                                 tr_n=tr["net"].get("trades", 0), tr_pf=tr["net"].get("profit_factor"),
                                 tr_yrs=tr["pct_years_positive"], va_sh=va["net"]["sharpe"], va_n=va["net"].get("trades", 0),
                                 rejected=rec["rejected_signal_bars"]))
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "v3_gen7_campaign.csv", index=False)
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_rows", 300, "display.max_colwidth", 90)
    print(main().round(2).to_string())

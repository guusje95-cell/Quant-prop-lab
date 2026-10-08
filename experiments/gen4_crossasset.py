"""Generation 4 - H6: does noise-area intraday momentum generalize to other CME-tradable markets
in their own primary sessions? Pre-registered sessions (ET) and a 4-variant grid; TRAIN screen,
then VALIDATION for survivors. OOS untouched."""
from __future__ import annotations
import itertools, json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.instruments import get
from qpl.research import pipeline as P, registry as R

H6 = {"family": "momentum/volatility breakout (cross-asset)", "hypothesis": "Escapes from a time-of-day noise area around the session open predict same-session continuation in gold, crude oil and EUR/GBP FX (and DAX as a non-tradable confirmation).",
      "rationale": "Intraday momentum is documented across asset classes (Gao et al. 2018 equities; Elaut, Frommel & Lampaert 2018 FX; commodity futures studies): hedging/stop flows and late-informed traders.",
      "sessions_ET": {"GC": "08:30-13:30", "CL(Brent proxy)": "09:00-14:30", "6E/6B": "08:00-12:00", "DAX": "03:00-11:30"},
      "falsification": "TRAIN net Sharpe <= 0.5 for the paper default and frozen-H3 variants; or VALIDATION Sharpe <= 0.3."}
MKTS = {  # fut: (proxy, open_min, close_min)
    "GC": ("XAUUSD", 510, 810), "CL": ("BRENT", 540, 870), "6E": ("EURUSD", 480, 720), "6B": ("GBPUSD", 480, 720),
    "DAX_confirm": ("DE40", 180, 690)}
GRID = [dict(lookback=14, mult=m, trail="band_mean", check_min=c) for m, c in itertools.product([1.0, 1.25], [30, 60])]
SPL = {"train": P.SPLITS["train"], "validation": P.SPLITS["validation"]}


def main():
    R.register_hypothesis("H6_XASSET_NOISE", H6["family"], 4, H6)
    rows = []
    for fut, (proxy, om, cm) in MKTS.items():
        ctx = P.context("dukascopy", proxy, "M15", om, cm)
        days = P.trading_days(ctx)
        inst = get(fut if fut != "DAX_confirm" else "ES")   # DAX: costs approximated with ES-like ticks (confirmation only)
        for prm in GRID:
            tr = P.backtest("noise_area", ctx, prm, inst)
            u = P.usd(tr, inst, contracts=1, norm=fut != "DAX_confirm")
            sm = P.split_metrics(u, days, SPL)
            g = P.split_metrics(P.usd(tr, inst, contracts=1, cost_mult=0, slip_mult=0, norm=fut != "DAX_confirm"), days, SPL)
            for s, m in sm.items():
                R.record(generation=4, family=H6["family"], hypothesis_id="H6_XASSET_NOISE", strategy="noise_area",
                         instrument=fut, data_source=f"dukascopy:{proxy}", timeframe="M15", params={**prm, "session": [om, cm]},
                         stage=f"screen_{s}", period=s, metrics=m, decision="info", reason="gen4 cross-asset screen")
            rows.append(dict(mkt=fut, prm=json.dumps(prm), tr_sh=sm["train"]["sharpe"], tr_gross=g["train"]["sharpe"],
                             va_sh=sm["validation"]["sharpe"], va_gross=g["validation"]["sharpe"], tr_n=sm["train"].get("trades"),
                             tr_years=sm["train"]["years"]))
    df = pd.DataFrame(rows)
    df.to_csv(Path(__file__).resolve().parents[1] / "results" / "gen4_crossasset.csv", index=False)
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 200, "display.max_colwidth", 80)
    print(main().round(2).to_string())

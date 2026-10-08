"""Final untouched test on real CME futures (protocol: config/final_test_protocol.json)."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A
from qpl.instruments import get
from qpl.research import pipeline as P, registry as R
from qpl.statistics import metrics as M, tests as T

ROOT = Path(__file__).resolve().parents[1]
PROT = json.loads((ROOT / "config" / "final_test_protocol.json").read_text())
FROZEN = PROT["candidate"]["params"]


def run_ctx(ctx, sym, norm):
    days = P.trading_days(ctx); inst = get(sym)
    tr = P.backtest("noise_area", ctx, FROZEN, inst)
    u = P.usd(tr, inst, contracts=1, norm=norm)
    return u, days, tr


def calibration():
    """Hourly approximation on Dukascopy US100 H1 (dev + OOS)."""
    ctx = P.context("dukascopy", "US100", "H1", 540, 960)
    u, days, _ = run_ctx(ctx, "NQ", True)
    sm = P.split_metrics(u, days, {"dev": ("2013-01-01", "2020-12-31"), "oos": ("2021-01-01", "2023-09-11")})
    d = A.daily_pnl(u, days)["pnl"].loc["2013-01-01":"2023-09-11"]
    return sm, d


def main(stage):
    out = {}
    if stage == "calibrate":
        sm, d = calibration()
        out = {k: {"sharpe": v["sharpe"], "total": v["total_usd"], "trades": v.get("trades")} for k, v in sm.items()}
        # bootstrap distribution of a 13-month (~270-day) Sharpe for the approximation
        rng = np.random.default_rng(5)
        idx = T.stationary_bootstrap_indices(len(d), 2000, 5, rng)[:, :270]
        x = d.to_numpy()[idx]
        sh = x.mean(1) / x.std(1) * np.sqrt(252)
        out["boot_270d_sharpe_pcts"] = {q: float(np.percentile(sh, q)) for q in (5, 25, 50, 75, 95)}
        out["boot_270d_p_sharpe_gt0"] = float(np.mean(sh > 0))
    elif stage == "test":
        res = {}
        for sym in ("NQ", "MNQ"):
            # Test B: hourly approximation, 13 months
            ctx = P.context("topstepx", sym, "1h", 540, 960)
            u, days, tr = run_ctx(ctx, sym, False)
            m = P.split_metrics(u, days, {"B": ("2025-03-21", "2026-04-15")})["B"]
            stress = {}
            for lab, cm in (("cost2x", 2.0), ("cost3x", 3.0)):
                uu = P.usd(tr, get(sym), contracts=1, cost_mult=cm, slip_mult=cm, norm=False)
                stress[lab] = P.split_metrics(uu, days, {"B": ("2025-03-21", "2026-04-15")})["B"]["sharpe"]
            d = A.daily_pnl(u, days)["pnl"].loc["2025-03-21":"2026-04-15"]
            res[f"B_{sym}"] = {"metrics": m, "stress_sharpe": stress, "monthly": {str(k): float(v) for k, v in M.monthly(d).items()},
                               "nw": T.newey_west_t(d.to_numpy())}
            # Test A: exact 15-minute specification, Jan-Apr 2026
            ctx = P.context("topstepx", sym, "15min")
            u, days, tr = run_ctx(ctx, sym, False)
            m = P.split_metrics(u, days, {"A": ("2026-01-20", "2026-04-15")})["A"]
            res[f"A_{sym}"] = {"metrics": m, "trades": u[["entry_ts", "exit_ts", "dir", "entry_px", "exit_px", "reason", "pnl_usd"]].astype(str).to_dict("records")}
            R.record(generation=6, family="H3_NOISE", hypothesis_id="H3_NOISE", strategy="noise_area", instrument=sym,
                     data_source="topstepx", timeframe="1h(approx)+15min(exact)", params=FROZEN, stage="FINAL_TEST",
                     period="2025-03-21..2026-04-15", metrics={"B": res[f"B_{sym}"]["metrics"], "A": m},
                     decision="final_test", reason="single pre-registered final test on real futures")
        out = res
    (ROOT / "results" / f"final_test_{stage}.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    st = sys.argv[1]
    r = main(st)
    if st == "calibrate":
        print(json.dumps(r, indent=1))
    else:
        for k, v in r.items():
            m = v["metrics"]
            print(k, "sharpe %.2f total %.0f trades %s maxdd %.0f winrate %.2f pf %.2f" % (m["sharpe"], m["total_usd"], m.get("trades"), m["max_dd_usd"], m.get("win_rate", np.nan), m.get("profit_factor", np.nan)))
            if k.startswith("B"):
                print("   stress", v["stress_sharpe"], "NW", v["nw"]); print("   monthly", {a: round(b) for a, b in v["monthly"].items()})

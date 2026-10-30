"""Income question (user, 2026-10-30): does a futures prop account NEXT TO the crypto accounts add meaningful monthly cash, at honest
live-Sharpe assumptions? Model estimate only (firm terms ASSUMED, unverified). Writes results/hub_research/income_futures.json.
Crypto: 2 x HyroTrader Two-Step $200k (start day 0 and 180), v9.8 hourly unit book shifted to the assumed live Sharpe (hub income engine).
Futures: k x 50k swing-firm accounts (terms of scripts/futures_prop_update.py, ASSUMED), futures book daily, scaled to 15% vol, shifted to the
assumed live Sharpe (252-day annualisation), challenge risk 1.0 / funded 0.5 (Gen191), worst day = 1.3 x the close loss; an independent
bootstrap path (daily correlation with crypto 0.04); $50 a month platform / data cost per futures account (assumption)."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import fbook
from qpl.hub import income
from qpl.lab import propfirms as PF
FIRM = PF.Firm("Swing futures firm 50k (ASSUMED)", 50_000, 150, (0.06,), 0.0, "initial", True, 0.04, "trailing_lock", False,
               2, 0, 0.90, 14, 0.0, False, 0.0, "ASSUMED terms", payout_min=250)
PATHS, H_DAYS, FX = 300, 730, 1.08


def futures_months(sharpe, n_acc, seed=9):
    b = fbook.build(fbook.sleeves()).loc["2010-06-01":"2026-09-30"]
    u = b * 0.15 / (b.std() * np.sqrt(252)); u = u - (u.mean() - sharpe * u.std() / np.sqrt(252))
    rng = np.random.default_rng(seed); n_td = int(H_DAYS * 5 / 7); months = H_DAYS // 30; Mo = np.zeros((PATHS, months)); x = u.to_numpy()
    for k in range(PATHS):
        idx = np.concatenate([np.arange(s, s + 20) for s in rng.integers(0, len(x) - 20, n_td // 20 + 1)])[:n_td]
        r = x[idx]; cal = np.arange(n_td) * 7 / 5
        cash_td = np.zeros(n_td)
        for a in range(n_acc):                                  # same signals: accounts share the path (start together)
            L = PF._ledger(r * 1.0, np.minimum(r, 0) * 1.3, np.maximum(r, 0), r * 0.5, np.minimum(r, 0) * 0.65, np.maximum(r, 0) * 0.5, cal, 0, n_td, FIRM, 3)
            cash_td += np.diff(np.concatenate([[0.0], L["wealth"]]))
        day = (cal).astype(int); cash = np.bincount(day, weights=cash_td, minlength=H_DAYS)[:H_DAYS] - 50.0 * n_acc / 30
        Mo[k] = cash[: months * 30].reshape(months, 30).sum(axis=1) / FX
    return Mo


hc = pd.read_parquet(ROOT / "results/v98b_book_hourly.parquet")["book"]
out = {"assumptions": __doc__, "results": []}
for cs in (1.65, 1.3):                                         # crypto: planning level and a weaker case
    sc = dict(income.SCENARIOS["conservative"]); sc["live_sharpe"] = cs
    C = income.simulate(hc, sc, n_paths=PATHS, return_paths=True)["monthly_paths_eur"]
    def summ(M):
        y2 = M[:, 12:24]
        return {"year-2 mean month EUR": round(float(y2.mean())), "year-2 p10 month EUR": round(float(np.percentile(y2, 10))),
                "P(month >= 10k) year 2": round(float((y2 >= 10_000).mean()), 2), "2-year total p50 EUR": round(float(np.percentile(M.sum(axis=1), 50))),
                "P(2-year loss)": round(float((M.sum(axis=1) < 0).mean()), 2)}
    out["results"].append({"crypto live Sharpe": cs, "futures": "none", **summ(C)})
    for fs in (0.65, 1.0, 1.5):
        for n in (1, 3):
            Fm = futures_months(fs, n)
            out["results"].append({"crypto live Sharpe": cs, "futures": f"{n} x 50k at live Sharpe {fs}", "futures alone year-2 mean month EUR": round(float(Fm[:, 12:24].mean())),
                                   **summ(C + Fm)})
            print(out["results"][-1], flush=True)
(ROOT / "results/hub_research/income_futures.json").write_text(json.dumps(out, indent=1, default=str))

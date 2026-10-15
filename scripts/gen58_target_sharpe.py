"""Gen58: what portfolio quality do we need? Synthetic daily return series with a given Sharpe (fat tails, t4), 15% annual vol in
the challenge and 6% (0.4x) or 9% (0.6x) when funded, run through the same prop engine and firm presets as the real strategies.
Calibration row: C* + BTC leads' real hourly-replay numbers (Gen55). 20 simulated 12-year histories per Sharpe level.
Writes results/gen58_target_sharpe.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF

FIRMS = {"FTMO 2-Step": PF.PRESETS["FTMO 2-Step $100k"], "HyroTrader 2-Step": PF.PRESETS["HyroTrader Two-Step $100k"],
         "HyroTrader 1-Step": PF.PRESETS["HyroTrader One-Step $100k"], "CFT 1-Phase": PF.PRESETS["Crypto Fund Trader 1-Phase $100k"]}
VOL = 0.15; DAYS = 365 * 12


def series(sr, seed):
    rng = np.random.default_rng(seed)
    sd = VOL / np.sqrt(365)
    z = rng.standard_t(4, DAYS) / np.sqrt(2.0)                        # unit variance, fat tails
    r = sr * VOL / 365 + sd * z
    wick = np.abs(rng.normal(0, 0.6 * sd, (2, DAYS)))
    idx = pd.date_range("2010-01-01", periods=DAYS, freq="D")
    return pd.DataFrame({"net": r, "worst": np.minimum(r, 0) - wick[0], "best": np.maximum(r, 0) + wick[1]}, index=idx)


def months_with_income(d, f, sf):
    cal = ((d.index - d.index[0]).days).to_numpy()
    rc = [d[c].to_numpy() for c in ("net", "worst", "best")]; rf = [x * sf for x in rc]
    out = []
    for s in range(0, len(cal) - 730, 60):
        led = PF._ledger(*rc, *rf, cal, s, s + 730, f, 5)
        cash = np.diff(np.r_[0.0, led["wealth"]])
        m = pd.Series(cash).groupby(np.arange(len(cash)) // 30.4).sum().iloc[6:]
        out.append((m > 0).mean())
    return float(np.mean(out))


rows = []
for sr in (1.0, 1.5, 2.0, 2.5, 3.0):
    for fn, f in FIRMS.items():
        for sf in (0.4, 0.6):
            acc = []
            for seed in range(20):
                d = series(sr, seed)
                a = PF.attempts(d, f, 1.0, step=7)
                p = PF.pipeline(d, f, 5, 1, 1.0, sf, horizon_days=730, step=15)
                acc.append(dict(pass_=a["P_pass"], days=a["median_days_to_pass"], net=p["net_mean"], p10=p["net_p10"], pprofit=p["P_profit"],
                                mi=months_with_income(d, f, sf), pos_m=((1 + d.net).resample("ME").prod() - 1 > 0).mean()))
            a = pd.DataFrame(acc).mean()
            rows.append(dict(sharpe=sr, firm=fn, risk_funded=sf, pass_rate=a.pass_, median_days_to_pass=a.days, net_2y=a.net, net_2y_p10=a.p10,
                             p_profit=a.pprofit, months_with_income=a.mi, positive_months_strategy=a.pos_m))
            print({k: round(v, 3) if isinstance(v, float) else v for k, v in rows[-1].items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen58_target_sharpe.csv", index=False)

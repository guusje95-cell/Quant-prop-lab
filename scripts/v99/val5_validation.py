"""VAL-5 (validation, 0 trials): statistical validity battery for the four current books.
  - observed Sharpe, autocorrelation-adjusted (Lo 2002) Sharpe
  - stationary block bootstrap of the Sharpe (mean block 20 days, 2,000 draws): 5 / 50 / 95%
  - Deflated Sharpe Ratio (Bailey & Lopez de Prado) at N = 2,038 trials: P(true SR > expected max of N zero-edge trials)
  - project planning haircut: SR - E[max SR of N nulls]
  - Monte Carlo (block bootstrap, 1-year paths, 5,000 paths) at 10% annual vol: max drawdown median / 95th percentile,
    P(max drawdown worse than -10%), P(1-year return < 0)
Books: crypto v9.9e (2022-01..2026-09, 365 d / yr), CFD bf2.8 (same), futures swing + CX4 (2010-06..2026-09 and 2023-26, 252), futures
daily-flat equity book DF-1c (same). Writes results/v99/val5_validation.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import kurtosis, norm, skew
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import fbook
from qpl.live import futures_cx as FX
G = 0.5772156649; N = 2038; rng = np.random.default_rng(11)
emax = lambda n: (1 - G) * norm.ppf(1 - 1 / n) + G * norm.ppf(1 - 1 / (n * np.e))
dd = lambda h: h.groupby(h.index.floor("D")).sum()


def boot_idx(n, L=20):
    idx = []
    while len(idx) < n:
        s = rng.integers(0, n); l = rng.geometric(1 / L); idx += [(s + i) % n for i in range(l)]
    return np.array(idx[:n])


def battery(x: pd.Series, ann: int, n_family: int | None = None, plan_sr: float | None = None) -> dict:
    r = x.dropna().to_numpy(); T = len(r); sd = r.std(ddof=1); srd = r.mean() / sd; SR = srd * np.sqrt(ann)
    g3, g4 = skew(r), kurtosis(r, fisher=False)
    eta = ann / np.sqrt(ann + 2 * sum((ann - k) * pd.Series(r).autocorr(k) for k in range(1, 31)))
    bs = np.array([(lambda y: y.mean() / y.std(ddof=1) * np.sqrt(ann))(r[boot_idx(T)]) for _ in range(2000)])
    dsr = norm.cdf((srd - emax(N) / np.sqrt(T)) * np.sqrt(T - 1) / np.sqrt(1 - g3 * srd + (g4 - 1) / 4 * srd ** 2))
    plan = SR - emax(N) / np.sqrt(T) * np.sqrt(ann)
    z = r / sd * (0.10 / np.sqrt(ann)); mdd, neg = [], []
    for _ in range(5000):
        y = z[boot_idx(T)[:ann]]; eq = np.cumprod(1 + y); mdd.append(float((eq / np.maximum.accumulate(eq) - 1).min())); neg.append(eq[-1] < 1)
    mdd = np.array(mdd)
    extra = {}
    if n_family:
        extra[f"DSR at N = {n_family} (this family's own trials)"] = round(float(norm.cdf((srd - emax(n_family) / np.sqrt(T)) * np.sqrt(T - 1) / np.sqrt(1 - g3 * srd + (g4 - 1) / 4 * srd ** 2))), 3)
        extra[f"planning at N = {n_family}"] = round(float(SR - emax(n_family) / np.sqrt(T) * np.sqrt(ann)), 2)
    if plan_sr is not None:                                          # Monte Carlo with the mean shrunk to the planning Sharpe (honest)
        zp = z - z.mean() + plan_sr * 0.10 / ann; m2, n2 = [], []
        for _ in range(5000):
            y = zp[boot_idx(T)[:ann]]; eq = np.cumprod(1 + y); m2.append(float((eq / np.maximum.accumulate(eq) - 1).min())); n2.append(eq[-1] < 1)
        m2 = np.array(m2)
        extra[f"MC at planning Sharpe {plan_sr}: max DD median / p95"] = [round(float(np.median(m2)), 3), round(float(np.percentile(m2, 5)), 3)]
        extra["MC at planning: P(max DD < -10%) / P(1-yr return < 0)"] = [round(float((m2 < -0.10).mean()), 3), round(float(np.mean(n2)), 3)]
    return {"days": T, "Sharpe": round(float(SR), 2), "Lo-adjusted Sharpe": round(float(srd * eta), 2), "skew / kurtosis": [round(float(g3), 2), round(float(g4), 1)],
            "bootstrap Sharpe 5% / 50% / 95%": [round(float(np.percentile(bs, q)), 2) for q in (5, 50, 95)],
            "P(bootstrap Sharpe < 0)": round(float((bs < 0).mean()), 4), "DSR at N = 2,038": round(float(dsr), 3),
            "planning (SR - E[max of N nulls])": round(float(plan), 2),
            "MC 1 yr at 10% vol: max DD median / p95": [round(float(np.median(mdd)), 3), round(float(np.percentile(mdd, 5)), 3)],
            "MC P(max DD < -10%)": round(float((mdd < -0.10).mean()), 3), "MC P(1-yr return < 0)": round(float(np.mean(neg)), 3), **extra}


out = {}
v = dd(pd.read_parquet(ROOT / "results/v99/v99e_series.parquet").iloc[:, 0]).loc["2022-01-01":"2026-09-30"]
b = dd(pd.read_parquet(ROOT / "results/v99/bf28_series.parquet").iloc[:, 0]).loc["2022-01-01":"2026-09-30"]
out["crypto v9.9e (2022-26)"] = battery(v, 365, plan_sr=2.05); out["CFD bf2.8 (2022-26)"] = battery(b, 365, plan_sr=1.55)
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet")
P["CX"] = pd.read_parquet(FX.PREFIX)["CX"].add(pd.read_parquet(FX.PREFIX4)["legs"], fill_value=0.0).reindex(P.index).fillna(0.0)
fx = FX.book(P)[0]
out["futures swing + CX4 (2010-26)"] = battery(fx.loc["2010-06-01":"2026-09-30"], 252, 450, 0.9); out["futures swing + CX4 (2023-26, out of sample)"] = battery(fx.loc["2023":"2026-09-30"], 252, 450)
df = fbook.build(pd.read_parquet(ROOT / "results/v99/df1c_sleeves.parquet"))
out["futures daily-flat DF-1c (2010-26)"] = battery(df.loc["2010-06-01":"2026-09-30"], 252, 450, 0.5); out["futures daily-flat DF-1c (2023-26)"] = battery(df.loc["2023":"2026-09-30"], 252, 450)
print(json.dumps(out, indent=1)); (ROOT / "results/v99/val5_validation.json").write_text(json.dumps(out, indent=1))

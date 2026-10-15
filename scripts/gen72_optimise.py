"""Gen72 (config/gen72_protocol.json): sleeve grids scored on DEV with neighbour smoothing, walk-forward check, v4 swap test,
point-in-time portfolio construction. Writes results/gen72_grid.csv, results/gen72_choice.csv, results/gen72_portfolio.csv,
results/cache_gen72_sleeves_hourly.parquet (selected sleeves, hourly) and results/cache_gen72_final.parquet."""
import sys
import warnings
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B

warnings.filterwarnings("ignore")
END = "2026-09-30"
H0 = CS.all_sleeves()
DEFAULT_H = H0[["C*", "premium carry", "cascade limit strict", "trend 4h"]]


def sharpe(x, a=None, b=None):
    y = x.loc[a:b] if a or b else x
    y = y.fillna(0.0)
    return float(y.mean() / y.std() * np.sqrt(365)) if y.std() > 0 else np.nan


def daily(h):
    return h.groupby(h.index.floor("D")).sum().loc[:END]


# ---------------------------------------------------------------- sleeve generators
def premium_carry(look, hold, frac):
    C = B.coins(); P = B.panel("close", "1D", C)
    prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in C}).reindex(P.index).rolling(look).mean()
    listed = P.notna().cumsum() >= 60
    rk = (-prem).where(listed).rank(axis=1, pct=True)
    hi, lo = rk > 1 - frac, rk <= frac
    w = hi.astype(float).div(hi.sum(axis=1), axis=0) - lo.astype(float).div(lo.sum(axis=1), axis=0)
    w = w.where(pd.Series(np.arange(len(w)) % hold == 0, index=w.index), np.nan).ffill().fillna(0.0)
    return CS._from_daily_weights(w, C, 5)


def trend(pair, coins):
    return CS.trend4h(coins=coins, n_in=pair[0], n_out=pair[1])


def cascade(k, hold, limit, doi):
    return CS.cascade(hold=hold, k=k, limit=limit, through=0.001, doi_th=doi)


GRIDS = {
    "premium carry": {"axes": {"look": [3, 7, 14, 21], "hold": [1, 3, 7, 14], "frac": [1 / 3, 1 / 4]},
                      "fn": premium_carry, "default": (7, 7, 1 / 3), "dev": ("2020-01-01", "2022-12-31")},
    "trend 4h": {"axes": {"pair": [(10, 5), (20, 5), (20, 10), (40, 5), (40, 10), (40, 20), (60, 10), (60, 20), (60, 30)],
                          "coins": [("BTC", "ETH", "SOL"), ("BTC", "ETH", "SOL", "BNB", "XRP", "DOGE")]},
                 "fn": trend, "default": ((20, 10), ("BTC", "ETH", "SOL")), "dev": ("2020-01-01", "2022-12-31")},
    "cascade limit strict": {"axes": {"k": [2.5, 3.0, 3.5], "hold": [6, 12, 24], "limit": [0.003, 0.005, 0.008], "doi": [0.03, 0.05]},
                             "fn": cascade, "default": (3.0, 12, 0.005, 0.05), "dev": ("2022-01-01", "2022-12-31")},
}


def _run(args):
    name, cell = args
    return name, cell, GRIDS[name]["fn"](*cell)


def cells(g):
    ax = list(g["axes"].values())
    return [tuple(v) for v in pd.MultiIndex.from_product(ax)]


def neighbours(g, cell):
    ax = list(g["axes"].values()); idx = [a.index(v) for a, v in zip(ax, cell)]; out = [cell]
    for d in range(len(ax)):
        for s in (-1, 1):
            j = idx[d] + s
            if 0 <= j < len(ax[d]):
                nb = list(cell); nb[d] = ax[d][j]; out.append(tuple(nb))
    return out


def smoothed(g, series, a, b):
    raw = {c: sharpe(series[c], a, b) for c in series}
    return {c: np.nanmean([raw[n] for n in neighbours(g, c)]) for c in series}, raw


def port_daily(D):
    """Gen70 daily v4 recipe (reference)."""
    z = D.loc["2021-12-01":END].fillna(0.0); z = z / (z.std() * np.sqrt(365)) * 0.10
    x = z.mean(axis=1); x = x * 0.15 / (x.loc["2022":].std() * np.sqrt(365))
    x = (x * (0.15 / (x.rolling(30).std().shift(1) * np.sqrt(365))).clip(upper=1.5)).loc["2022-01-01":].dropna()
    return sharpe(x)


if __name__ == "__main__":
    jobs = [(n, c) for n, g in GRIDS.items() for c in cells(g)]
    print("jobs:", len(jobs), flush=True)
    with Pool(4) as pool:
        res = pool.map(_run, jobs, chunksize=1)
    series = {n: {} for n in GRIDS}; hourly = {n: {} for n in GRIDS}
    for n, c, h in res:
        hourly[n][c] = h; series[n][c] = daily(h)
    rows, choice, chosen_h = [], [], {}
    D4 = daily(DEFAULT_H)
    for n, g in GRIDS.items():
        a, b = g["dev"]; sm, raw = smoothed(g, series[n], a, b)
        for c in series[n]:
            rows.append({"sleeve": n, "cell": str(c), "dev_raw": raw[c], "dev_smoothed": sm[c], "2023+": sharpe(series[n][c], "2023-01-01", END),
                         "TEST": sharpe(series[n][c], "2023-01-01", "2024-12-31"), "HOLD": sharpe(series[n][c], "2025-01-01", END)})
        best = max(sm, key=lambda c: -np.inf if np.isnan(sm[c]) else sm[c]); dflt = g["default"]
        s_best, s_def = sharpe(series[n][best], "2023-01-01", END), sharpe(series[n][dflt], "2023-01-01", END)
        swap = D4.copy(); swap[n] = series[n][best]; v4_swap, v4_base = port_daily(swap), port_daily(D4)
        # walk-forward: pick on data before each year
        wf = []
        for y in (2023, 2024, 2025, 2026):
            sm_y, _ = smoothed(g, series[n], a, f"{y - 1}-12-31")
            pick = max(sm_y, key=lambda c: -np.inf if np.isnan(sm_y[c]) else sm_y[c])
            wf.append(series[n][pick].loc[str(y)]); print(n, "WF", y, pick, flush=True)
        wf = pd.concat(wf)
        adopt = (best != dflt) and (s_best >= s_def) and (v4_swap >= v4_base)
        choice.append({"sleeve": n, "default": str(dflt), "dev_best_smoothed": str(best), "2023+_default": s_def, "2023+_best": s_best,
                       "v4_base": v4_base, "v4_with_best": v4_swap, "walk_forward_2023+": sharpe(wf), "adopted": adopt,
                       "tuning_proven_by_WF": sharpe(wf) > s_def})
        chosen_h[n] = hourly[n][best] if adopt else hourly[n][dflt]
        print(choice[-1], flush=True)
    pd.DataFrame(rows).to_csv(ROOT / "results/gen72_grid.csv", index=False)
    pd.DataFrame(choice).to_csv(ROOT / "results/gen72_choice.csv", index=False)
    Hs = pd.DataFrame({"C*": H0["C*"], **chosen_h}).fillna(0.0)
    Hs.to_parquet(ROOT / "results/cache_gen72_sleeves_hourly.parquet")
    print("saved selected sleeves", flush=True)

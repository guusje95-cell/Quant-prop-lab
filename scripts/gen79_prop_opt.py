"""Gen79 (config/gen79_protocol.json): per-firm prop deployment optimisation (risk in challenge / funded, own daily stop),
chosen on DEV 2022-24 bootstrap, verified on HOLD 2025-26 bootstrap. Writes results/gen79_grid.csv and results/gen79_choice.csv."""
import sys
import warnings
from itertools import product
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF

warnings.filterwarnings("ignore")
SC, SF, ST = [0.75, 1.0, 1.25, 1.5], [0.4, 0.6, 0.8, 1.0], [0.4, 0.5, 0.6, 0.75]
DEV, HOLD = ("2022-01-01", "2024-12-31 23:00"), ("2025-01-01", "2026-09-30 23:00")


def to_daily_stop(h, stop):
    rows = []
    for d, gg in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + gg.to_numpy())
        if stop > 0 and (p <= 1 - stop).any():
            k = int(np.argmax(p <= 1 - stop)); close = p[k] - 0.001
            rows.append((d, close - 1, min(p[:k + 1].min(), close) - 1, max(p[:k + 1].max(), 1.0) - 1))
        else:
            rows.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day")


def scaled15(h):
    d = h.groupby(h.index.floor("D")).sum().loc["2022-01-01":"2026-09-30"]
    return h.loc["2022-01-01":"2026-09-30 23:00"] * 0.15 / (d.std() * np.sqrt(365))


V5 = pd.read_parquet(ROOT / "results/cache_gen72_final.parquet")["portfolio"].loc["2022-01-01":"2026-09-30 23:00"]
CFD = scaled15(pd.read_parquet(ROOT / "results/cache_gen74_hourly.parquet")["swap 3.3 (base)"])
BOOKS = {"crypto": (V5, ["HyroTrader One-Step $100k", "HyroTrader Two-Step $100k", "SizeProp One-Step $100k", "Crypto Fund Trader 1-Phase $100k"], 0.95),
         "cfd": (CFD, ["FTMO 2-Step $100k", "FundedNext Stellar 2-Step $100k", "BrightFunded Two-Step Classic $100k"], 0.88)}


def evaluate(h, f, sc, sf, st, per):
    hh = h.loc[per[0]:per[1]]
    hc = to_daily_stop(hh * sc, st * f.daily_loss); hf = to_daily_stop(hh * sf, st * f.daily_loss)
    pb = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, method="bootstrap", n_boot=300, block=20, seed=11)
    return {"mean": pb["net_mean"], "p10": pb["net_p10"], "pprof": pb["P_profit"]}


rows, choice = [], []
for book, (h, firms, pmin) in BOOKS.items():
    for key in firms:
        f = PF.PRESETS[key]; grid = {}
        for sc, sf, st in product(SC, SF, ST):
            grid[(sc, sf, st)] = evaluate(h, f, sc, sf, st, DEV)
        idx = {k: (SC.index(k[0]), SF.index(k[1]), ST.index(k[2])) for k in grid}
        ok = {k: v["pprof"] >= pmin and v["p10"] >= 0 for k, v in grid.items()}

        def score(k):
            nb = [k]
            for ax in range(3):
                for s in (-1, 1):
                    j = list(idx[k]); j[ax] += s
                    if 0 <= j[ax] < 4:
                        nb.append((SC[j[0]], SF[j[1]], ST[j[2]]))
            return float(np.mean([grid[n]["mean"] for n in nb]))
        cand = [k for k in grid if ok[k]]
        best = max(cand, key=score) if cand else (1.0, 0.6, 0.5)
        for k, v in grid.items():
            rows.append({"book": book, "firm": f.name, "risk_challenge": k[0], "risk_funded": k[1], "stop_frac": k[2], **{f"dev_{a}": b for a, b in v.items()},
                         "eligible": ok[k], "smoothed": score(k)})
        dflt = (1.0, 0.6, 0.5)
        hb, hd = evaluate(h, f, *best, HOLD), evaluate(h, f, *dflt, HOLD)
        adopt = best != dflt and hb["mean"] >= hd["mean"] and hb["pprof"] >= hd["pprof"] - 0.02
        full_b, full_d = evaluate(h, f, *best, ("2022-01-01", "2026-09-30 23:00")), evaluate(h, f, *dflt, ("2022-01-01", "2026-09-30 23:00"))
        choice.append({"book": book, "firm": f.name, "dev_pick": str(best), "dev_pick_dev_mean": grid[best]["mean"], "default_dev_mean": grid[dflt]["mean"],
                       "hold_pick_mean": hb["mean"], "hold_pick_p10": hb["p10"], "hold_pick_pprof": hb["pprof"],
                       "hold_default_mean": hd["mean"], "hold_default_p10": hd["p10"], "hold_default_pprof": hd["pprof"], "adopted": adopt,
                       "full_pick_mean": full_b["mean"], "full_pick_p10": full_b["p10"], "full_pick_pprof": full_b["pprof"],
                       "full_default_mean": full_d["mean"], "full_default_p10": full_d["p10"], "full_default_pprof": full_d["pprof"]})
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in choice[-1].items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen79_grid.csv", index=False)
pd.DataFrame(choice).to_csv(ROOT / "results/gen79_choice.csv", index=False)
print("done", flush=True)

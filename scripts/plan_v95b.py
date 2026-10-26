"""Account plan for v9.5 with the Gen413 sizing (challenge 1.5 instead of 2.0). Writes results/plan_v95b.json.
Book: results/gen404_book_hourly.parquet (research v9.5)."""
import json
import sys
from dataclasses import replace
from math import e
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
END = "2026-09-30"
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
b = unit(pd.read_parquet(ROOT / "results/gen404_book_hourly.parquet")["book"])
d = dd(b).loc["2022":END]; T = len(d); sr = d.mean() / d.std()
def plan(N):
    sr0 = np.sqrt(1.0 / T) * ((1 - 0.5772156649) * norm.ppf(1 - 1 / N) + 0.5772156649 * norm.ppf(1 - 1 / (N * e))); return float((sr - sr0) * np.sqrt(365))
PL = {f"N={N}": round(plan(N), 3) for N in (300, 1000, 1770)}
shift_to = lambda h, tg: h - (dd(h.loc["2022":]).mean() - tg * dd(h.loc["2022":]).std() / np.sqrt(365)) / 24
P = PF.PRESETS; HY = P["HyroTrader Two-Step $200k"]
CFT = replace(P["Crypto Fund Trader 2-Phase $100k"], name="CFT 2-Phase 200k", account=200000, fee=1200.0, targets=(0.08, 0.05))
MFP = replace(HY, name="MFP Signature 100k", account=100000, fee=696.0, targets=(0.10,), daily_loss=0.03, max_loss=0.06, max_type="static", min_days=0, payout_min=0)
CH = 1.5
ACC = [("1 HyroTrader $200k", HY, CH, 1.5, 0.5), ("2 CFT $200k", CFT, CH, 1.5, 0.5), ("3 MyFundedPerps $100k", MFP, 1.0, 2.0, 0.4)]
out = {"sizing": "challenge 1.5 / funded 1.5 / stop 0.5 (Gen413)", "backtest Sharpe 2022-26": round(float(sr * np.sqrt(365)), 3), "planning Sharpe": PL}
A, Z = "2025-01-01", END + " 23:00"
for lvl, tgt in (("backtest", None), ("planning N=1770", PL["N=1770"]), ("planning N=300", PL["N=300"]), ("weak live 1.0", 1.0)):
    ser = b if tgt is None else unit(shift_to(b, tgt)); x = ser.loc[A:Z]
    frames = {nm: (to_daily_stop(x * sc, st * f.daily_loss), to_daily_stop(x * sf, st * f.daily_loss)) for nm, f, sc, sf, st in ACC}
    idx = pd.DatetimeIndex(sorted(set.intersection(*[set(v[0].index) for v in frames.values()])))
    paths, cal0 = PF._paths(pd.DataFrame(index=idx, data={"net": 0.0}), "bootstrap", 730, 1, 400, 20, 11)
    per_day = len(idx) / max(1, cal0[-1]); NET = {}
    for nm, f, sc, sf, st in ACC:
        ch, fd = frames[nm]; ch, fd = ch.reindex(idx).fillna(0.0), fd.reindex(idx).fillna(0.0)
        rc, loc, hic = PF._arrays(ch, 1.0); rf, lof, hif = PF._arrays(fd, 1.0); nets = []
        for _, xx in paths:
            cal = (np.arange(len(xx)) / per_day).astype(int)
            nets.append(PF._ledger(rc[xx], loc[xx], hic[xx], rf[xx], lof[xx], hif[xx], cal, 0, len(xx), f, 5)["net"])
        NET[nm] = np.array(nets)
    N_ = pd.DataFrame(NET); q = lambda v, p: round(float(np.percentile(v, p)))
    res = {"per account": {nm: {"mean": round(float(N_[nm].mean())), "p10": q(N_[nm], 10), "P_profit": round(float((N_[nm] > 0).mean()), 3)} for nm in N_}, "stack": {}}
    for k in range(1, len(N_.columns) + 1):
        t = N_.iloc[:, :k].sum(axis=1); res["stack"][" + ".join(c.split(" ")[1] for c in N_.columns[:k])] = {"mean": round(float(t.mean())), "p10": q(t, 10), "P_loss": round(float((t < 0).mean()), 3)}
    out[lvl] = res; print(lvl, json.dumps(res), flush=True)
(ROOT / "results/plan_v95b.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in ("backtest Sharpe 2022-26", "planning Sharpe")}))

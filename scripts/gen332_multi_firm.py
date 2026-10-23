"""Gen332 (config/gen332_protocol.json): every planned firm account in ONE joint bootstrap. Needs results/gen333_series.parquet.
Writes results/gen332.json."""
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
S = pd.read_parquet(ROOT / "results/gen333_series.parquet")
v_by = S["Bybit"]; v_hl = S["H2 51 coins, altcoin cap 2x"]
bf = pd.read_parquet(ROOT / "results/cache_bf26_final.parquet")["portfolio"].loc["2022-01-01":"2026-09-30 23:00"]
P = PF.PRESETS; HY = P["HyroTrader Two-Step $200k"]
CFT = replace(P["Crypto Fund Trader 2-Phase $100k"], name="CFT 2-Phase 200k", account=200000, fee=1200.0, targets=(0.08, 0.05))
BF = replace(P["BrightFunded Two-Step Classic $200k"], fee=P["BrightFunded Two-Step Classic $200k"].fee * 1.1)
PROPR = replace(HY, name="Propr 2-Step 100k", account=100000, fee=749.0, targets=(0.05, 0.10), daily_loss=0.05, max_loss=0.08,
                max_type="trailing_lock", trailing_intraday=True, min_days=0, split=0.90, payout_min=0)
MFP = replace(HY, name="MFP Signature 100k", account=100000, fee=696.0, targets=(0.10,), daily_loss=0.03, max_loss=0.06, max_type="static",
              min_days=0, payout_min=0)
ACC = [("1 HyroTrader $200k", HY, "v_by", 1, 2.0, 1.5, 0.5, 0), ("2 CFT $200k (Bybit)", CFT, "v_by", 1, 2.0, 1.5, 0.5, 0),
       ("3 BrightFunded $200k (bf2.6)", BF, "bf", 1, 2.0, 1.5, 0.5, -2), ("4 Propr 3 x $100k", PROPR, "v_hl", 3, 1.0, 1.5, 0.6, 0),
       ("5 MyFundedPerps $100k", MFP, "v_by", 1, 1.0, 2.0, 0.4, 4)]
A, Z = "2025-01-01", "2026-09-30 23:00"


def sh(p):
    d = p.groupby(p.index.floor("D")).sum().loc["2022-01-01":]; return float(d.mean() / d.std() * np.sqrt(365))


def scaled(p, target=None):
    d = p.groupby(p.index.floor("D")).sum()
    if target is not None:
        p = p - (d.loc["2022-01-01":].mean() - target * d.loc["2022-01-01":].std() / np.sqrt(365)) / 24
    dd = p.loc[:"2024-12-31 23:00"]; dd = dd.groupby(dd.index.floor("D")).sum()
    return p * 0.15 / (dd.std() * np.sqrt(365))


out = {"platform Sharpe 2022-26": {"v8.6 Bybit": round(sh(v_by), 3), "v8.6 Hyperliquid 51": round(sh(v_hl), 3), "bf2.6 BrightFunded": round(sh(bf), 3)}}
for lvl, tgt in (("realistic", {"v_by": None, "v_hl": None, "bf": None}), ("planning", {"v_by": sh(v_by) - 1.25, "v_hl": sh(v_hl) - 1.25, "bf": 1.49})):
    ser = {"v_by": scaled(v_by, tgt["v_by"]), "v_hl": scaled(v_hl, tgt["v_hl"]), "bf": scaled(bf, tgt["bf"])}
    frames = {}
    for nm, f, k, n, sc, sf, st, reset in ACC:
        x = ser[k].loc[A:Z].copy(); x.index = x.index - pd.Timedelta(hours=reset)
        ch, fd = to_daily_stop(x * sc, st * f.daily_loss), to_daily_stop(x * sf, st * f.daily_loss)
        frames[nm] = (ch, fd)
    days = sorted(set.intersection(*[set(v[0].index) for v in frames.values()]))
    idx = pd.DatetimeIndex(days)
    paths, cal0 = PF._paths(pd.DataFrame(index=idx, data={"net": 0.0}), "bootstrap", 730, 1, 400, 20, 11)
    per_day = len(idx) / max(1, cal0[-1]); NET = {}; FEES = {}
    for nm, f, k, n, sc, sf, st, reset in ACC:
        ch, fd = frames[nm]; ch, fd = ch.reindex(idx).fillna(0.0), fd.reindex(idx).fillna(0.0)
        rc, loc, hic = PF._arrays(ch, 1.0); rf, lof, hif = PF._arrays(fd, 1.0)
        nets, fees = [], []
        for _, x in paths:
            cal = (np.arange(len(x)) / per_day).astype(int)
            g = PF._ledger(rc[x], loc[x], hic[x], rf[x], lof[x], hif[x], cal, 0, len(x), f, 5)
            nets.append(g["net"] * n); fees.append(g["fees"] * n)
        NET[nm] = np.array(nets); FEES[nm] = np.array(fees)
    N = pd.DataFrame(NET); tot = N.sum(axis=1)
    q = lambda v, p: round(float(np.percentile(v, p)))
    res = {"per account": {nm: {"mean": round(float(N[nm].mean())), "p10": q(N[nm], 10), "P_profit": round(float((N[nm] > 0).mean()), 3),
                                "fees mean": round(float(FEES[nm].mean()))} for nm in N},
           "total": {"mean": round(float(tot.mean())), "p5": q(tot, 5), "p10": q(tot, 10), "p50": q(tot, 50), "p90": q(tot, 90),
                     "P(total < 0)": round(float((tot < 0).mean()), 3), "fees mean": round(float(sum(FEES.values()).mean())),
                     "fees max": round(float(sum(FEES.values()).max()))},
           "P(every account loses money)": round(float((N < 0).all(axis=1).mean()), 3),
           "mean total when every account loses": round(float(tot[(N < 0).all(axis=1)].mean())) if (N < 0).all(axis=1).any() else None,
           "correlation of account outcomes (mean pairwise)": round(float(N.corr().values[np.triu_indices(len(N.columns), 1)].mean()), 3),
           "stack (accounts 1..k)": {}}
    for k in range(1, len(N.columns) + 1):
        t = N.iloc[:, :k].sum(axis=1)
        res["stack (accounts 1..k)"][" + ".join(c.split(" ")[1] for c in N.columns[:k])] = {"mean": round(float(t.mean())), "p10": q(t, 10), "P_loss": round(float((t < 0).mean()), 3)}
    out[lvl] = res; print(lvl, json.dumps(res), flush=True)
json.dump(out, open(ROOT / "results/gen332.json", "w"), indent=1, default=float)

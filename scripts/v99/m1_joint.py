"""v9.9 M1 step 2 (research/v99/m1_protocol.json): all planned firm accounts in ONE joint bootstrap at planning Sharpe levels
(Gen332 machinery). Needs results/v99/m1_series_bybit.parquet and m1_series_hl.parquet. Writes results/v99/m1_joint.json."""
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
import c1_cfd_port as C
from qpl.live import cfd_extra as X


def sh(p):
    d = p.groupby(p.index.floor("D")).sum().loc["2022-01-01":"2026-09-30"]; return float(d.mean() / d.std() * np.sqrt(365))


def scaled(p, target):
    d = p.groupby(p.index.floor("D")).sum()
    p = p - (d.loc["2022-01-01":].mean() - target * d.loc["2022-01-01":].std() / np.sqrt(365)) / 24
    dd = p.loc[:"2024-12-31 23:00"]; dd = dd.groupby(dd.index.floor("D")).sum()
    return p * 0.15 / (dd.std() * np.sqrt(365))


def main():
    B = pd.read_parquet(ROOT / "results/v99/m1_series_bybit.parquet"); Hh = pd.read_parquet(ROOT / "results/v99/m1_series_hl.parquet")
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    bf = C.book(BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()}))
    raw = {"A": B["capped"], "B": B["uncapped"], "C": Hh["uncapped"], "D": bf}
    SR = {k: sh(v) for k, v in raw.items()}; ded = SR["A"] - 1.95
    plan = {"A": 1.95, "B": SR["B"] - ded, "C": SR["C"] - ded, "D": 1.36}
    P = PF.PRESETS; HY = P["HyroTrader Two-Step $200k"]
    CFT = replace(P["Crypto Fund Trader 2-Phase $100k"], name="CFT 2-Phase 200k", account=200000, fee=1200.0, targets=(0.08, 0.05))
    BF = replace(P["BrightFunded Two-Step Classic $200k"], fee=P["BrightFunded Two-Step Classic $200k"].fee * 1.1)
    PROPR = replace(HY, name="Propr 2-Step 100k", account=100000, fee=749.0, targets=(0.05, 0.10), daily_loss=0.05, max_loss=0.08,
                    max_type="trailing_lock", trailing_intraday=True, min_days=0, split=0.90, payout_min=0)
    ACC = [("HyroTrader $200k", HY, "A", 1, 1.5, 1.5, 0.5, 0), ("BrightFunded $200k (bf2.7)", BF, "D", 1, 1.5, 1.5, 0.5, -2),
           ("CFT $200k (Bybit)", CFT, "B", 1, 1.5, 1.5, 0.5, 0), ("Propr 3 x $100k (Hyperliquid)", PROPR, "C", 3, 1.0, 1.0, 0.6, 0)]
    A_, Z_ = "2025-01-01", "2026-09-30 23:00"
    ser = {k: scaled(v, plan[k]) for k, v in raw.items()}
    frames = {}
    for nm, f, k, n, sc, sf, st, reset in ACC:
        x = ser[k].loc[A_:Z_].copy(); x.index = x.index - pd.Timedelta(hours=reset)
        frames[nm] = (to_daily_stop(x * sc, st * f.daily_loss), to_daily_stop(x * sf, st * f.daily_loss))
    days = pd.DatetimeIndex(sorted(set.intersection(*[set(v[0].index) for v in frames.values()])))
    paths, cal0 = PF._paths(pd.DataFrame(index=days, data={"net": 0.0}), "bootstrap", 730, 1, 400, 20, 11)
    per_day = len(days) / max(1, cal0[-1]); NET, FEES = {}, {}
    for nm, f, k, n, sc, sf, st, reset in ACC:
        ch, fd = frames[nm]; ch, fd = ch.reindex(days).fillna(0.0), fd.reindex(days).fillna(0.0)
        rc, loc, hic = PF._arrays(ch, 1.0); rf, lof, hif = PF._arrays(fd, 1.0); nets, fees = [], []
        for _, x in paths:
            cal = (np.arange(len(x)) / per_day).astype(int)
            g = PF._ledger(rc[x], loc[x], hic[x], rf[x], lof[x], hif[x], cal, 0, len(x), f, 5)
            nets.append(g["net"] * n); fees.append(g["fees"] * n)
        NET[nm] = np.array(nets); FEES[nm] = np.array(fees)
    N = pd.DataFrame(NET); q = lambda v, p: round(float(np.percentile(v, p)))
    out = {"backtest Sharpe 2022-26": {k: round(v, 3) for k, v in SR.items()}, "venue Sharpe by period": {k: C.full(v) for k, v in raw.items()},
           "planning Sharpe used": {k: round(v, 2) for k, v in plan.items()},
           "per account (2-year net USD)": {nm: {"mean": round(float(N[nm].mean())), "p10": q(N[nm], 10), "P_loss": round(float((N[nm] < 0).mean()), 3),
                                                 "fees mean": round(float(FEES[nm].mean()))} for nm in N},
           "stack": {}, "P(every account loses)": round(float((N < 0).all(axis=1).mean()), 3),
           "outcome correlation (mean pairwise)": round(float(N.corr().values[np.triu_indices(len(N.columns), 1)].mean()), 3)}
    for k in range(1, len(N.columns) + 1):
        t = N.iloc[:, :k].sum(axis=1)
        out["stack"][" + ".join(N.columns[:k])] = {"mean": round(float(t.mean())), "p10": q(t, 10), "p50": q(t, 50), "P_loss": round(float((t < 0).mean()), 3)}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/m1_joint.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

"""Gen129 (config/gen129_protocol.json): front-running the Goldman roll with calendar spreads. Writes results/gen129.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
SPL = (("2010-06-01", "2017-12-31"), ("2018-01-01", "2022-12-31"), ("2023-01-01", "2026-09-30"))


def spread_pnl(root, lead):
    d = F.daily(root); d = d[d.index.weekday < 5].dropna(subset=["near_far"])
    idx = d.index; pos = pd.Series(np.arange(len(idx)), index=idx)
    nf, pair, cost = d.near_far, d.pair, 2 * d.cost                       # 2 legs
    target = pd.Series(0.0, index=idx); entry_pair = pd.Series(np.nan, index=idx)
    for _, g in idx.to_series().groupby(idx.to_period("M")):
        if len(g) < 9:
            continue
        bd5 = pos[g.index[4]]; e = bd5 - lead
        if e < 1:
            continue
        sched = {idx[e + k]: 1.0 for k in range(1, lead + 1)}               # held through business day 5's close
        for j, w in zip(range(4, 9), (0.8, 0.6, 0.4, 0.2, 0.0)):            # unwind 20% at each close of days 5..9
            sched[g.index[j]] = w
        sched[idx[e]] = 1.0
        for t, w in sched.items():
            target[t] = max(target[t], w)
            if np.isnan(entry_pair[t]):
                entry_pair[t] = pair[idx[e]]
    held, pnl, w_prev, p_prev = [], [], 0.0, np.nan
    for i, t in enumerate(idx):
        r = 0.0
        if w_prev > 0 and i > 0:
            if pair[t] == pair[idx[i - 1]] == p_prev:
                r = -(nf[t] / nf[idx[i - 1]] - 1) * w_prev
            else:
                w_prev = 0.0                                                # pair no longer observable: closed at the previous close
        w = target[t] if (target[t] > 0 and (w_prev > 0 or pair[t] == entry_pair[t])) else 0.0
        if w_prev == 0 and w > 0 and target[t] < 1.0:
            w = 0.0                                                         # never open during the unwind days
        if w > 0 and w_prev > 0 and pair[t] != p_prev:
            w = 0.0
        tc = abs(w - w_prev) * cost[t]
        pnl.append(r - tc); p_prev = pair[t] if w > 0 else np.nan; w_prev = w
    return pd.Series(pnl, index=idx)


def sharpe(p, a, b):
    x = p.loc[a:b]; return float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else float("nan")


rows = []
ENERGY = ["CL", "HO", "RB", "NG"]; ALL12 = ENERGY + ["GC", "SI", "HG", "ZC", "ZS", "ZW", "LE", "HE"]
for name, members, lead in (("R1 Strategy 1 (10 days), energy, PRIMARY", ENERGY, 10), ("R2 Strategy 2 (5 days), energy", ENERGY, 5),
                            ("R3 Strategy 1, all 12", ALL12, 10)):
    P = pd.concat({r: spread_pnl(r, lead) for r in members}, axis=1).fillna(0.0)
    active = (P != 0).sum(axis=1).clip(lower=1); p = P.sum(axis=1) / active
    k = tuple(round(sharpe(p, a, b), 3) for a, b in SPL)
    per = {r: tuple(round(sharpe(P[r], a, b), 2) for a, b in SPL) for r in members}
    row = {"test": name, "DEV": k[0], "TEST": k[1], "HOLD": k[2], "pass": bool(k[0] > 0 and k[1] >= 0.5 and k[2] >= 0.3),
           "ann ret": round(float(p.mean() * 252), 4), "per market": per}
    rows.append(row); print(row, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen129.csv", index=False)

"""DF-3 (deployment, 0 alpha trials; FLAGGED as a post-hoc subset): the 8 equity-index sleeves of the exact daily-flat book (P1, R1, T1,
T2, FC, MM, OIL, K3; they only trade ES / NQ) as a book for CFD prop firms on US500 / US100 CFDs. Flat 16:00-18:00 ET (over the 17:00 ET
rollover: no swap) and at weekends, so no swap-free account is needed and many CFD firms (FTMO, FundedNext, The5ers, ...) qualify.
Futures returns as the CFD proxy (index CFDs track the futures; typical US500 / US100 CFD cost ~0.5 bp per side, close to the micro
futures cost used). FTMO-like $100K two-step: +10% / +5% targets, 5% daily loss (from the day's start balance), 10% static max loss,
fee $585 (refunded with the first payout), funded: payout every 14 days of 80% of the profit, account lost -> new challenge. 2 years,
2,000 paths, 10-day block bootstrap of 2023-26; full / half / ZERO edge. Writes results/v99/df3_cfd_prop.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import fbook
import futures_db as F

EQ = ["P1", "R1", "T1", "T2", "FC", "MM", "OIL", "K3"]
Q = pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet")[EQ]
book = fbook.build(Q); b = book.loc["2023-01-01":"2026-09-30"]; b = b[b.index.weekday < 5]
rng = np.random.default_rng(5)


def run(x, acct=100_000.0, days=504, fee=585.0):
    net, d, refund = 0.0, 0, 0.0
    while d < days:
        ok = True
        for tgt in (0.10, 0.05):                                            # two-step challenge
            bal = acct; net -= fee if tgt == 0.10 else 0.0; refund = fee if tgt == 0.10 else refund
            while d < days:
                day0 = bal; bal += x[d]; d += 1
                if bal <= acct * 0.90 or bal <= day0 - 0.05 * acct:
                    ok = False; break
                if bal >= acct * (1 + tgt):
                    break
            else:
                ok = False
            if not ok:
                break
        if not ok:
            continue
        bal, last = acct, d                                                # funded
        while d < days:
            day0 = bal; bal += x[d]; d += 1
            if bal <= acct * 0.90 or bal <= day0 - 0.05 * acct:
                break
            if d - last >= 14 and bal > acct:
                net += 0.8 * (bal - acct) + refund; refund = 0.0; bal = acct; last = d
    return net


def sim(r, vol, mode, paths=2000, days=504):
    r = r.to_numpy(); r = r / r.std() * vol / np.sqrt(252); r = r - {"full": 0.0, "half": 0.5, "zero": 1.0}[mode] * r.mean()
    out = []
    for _ in range(paths):
        idx = np.concatenate([np.arange(s, s + 10) % len(r) for s in rng.integers(0, len(r), days // 10 + 1)])[:days]
        out.append(run(r[idx] * 100_000.0))
    n = np.array(out); return {"mean": round(float(n.mean())), "p10": round(float(np.percentile(n, 10))), "P(net>0)": round(float((n > 0).mean()), 2)}


out = {"equity-index daily-flat book 2010-17 / 2018-22 / 2023-26": [round(F.sharpe(book, *s), 3) for s in F.SPLITS]}
for v in (0.06, 0.10, 0.14, 0.18):
    k = f"vol {v:.0%}"; out[k] = {m: sim(b, v, m) for m in ("full", "half", "zero")}
    out[k]["edge value (full - zero)"] = out[k]["full"]["mean"] - out[k]["zero"]["mean"]
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df3_cfd_prop.json").write_text(json.dumps(out, indent=1))

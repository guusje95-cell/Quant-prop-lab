"""Prop economics v2 for the daily-flat futures book (0 alpha trials). Topstep-like $50K with the rules reported by third-party sources
(UNVERIFIED; official pages to be snapshotted with get_prop_rules.bat):
  Combine: target +$3,000, end-of-day trailing max loss $2,000 (locks at the start balance), consistency: best day <= 50% of the total
           profit when passing (otherwise keep trading), $49 per started month.
  Express Funded: $149 activation, same trailing loss; payout after >= 5 winning days of >= $150 since the last payout, at most 50% of
           the profit above start and at most $5,000, 90% to the trader; account lost -> new Combine.
2 years, 2,000 paths, 10-day block bootstrap of the 2023-26 daily-flat book (DF-1); variants: full edge, half edge, ZERO edge (control).
Writes results/v99/df_prop2.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import fbook

Q = pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet").drop(columns=["CX4", "CXB"])
b = fbook.build(Q).loc["2023-01-01":"2026-09-30"]; b = b[b.index.weekday < 5]
rng = np.random.default_rng(11)


def run(x, acct=50_000.0, days=504):
    net, d = 0.0, 0
    while d < days:
        bal, hi, best, start, ok = acct, acct, 0.0, d, False                 # Combine
        while d < days:
            pnl = x[d]; bal += pnl; d += 1; hi = max(hi, bal); best = max(best, pnl)
            if bal <= min(hi, acct + 2000) - 2000:
                break
            if bal - acct >= 3000 and best <= 0.5 * (bal - acct):
                ok = True; break
        net -= 49 * ((d - start) // 21 + 1)
        if not ok:
            continue
        net -= 149; bal, hi, wins = acct, acct, 0                           # Express Funded
        while d < days:
            pnl = x[d]; bal += pnl; d += 1; hi = max(hi, bal); wins += pnl >= 150
            if bal <= min(hi, acct + 2000) - 2000:
                break
            if wins >= 5 and bal > acct:
                w = min(0.5 * (bal - acct), 5000.0); net += 0.9 * w; bal -= w; wins = 0
    return net


def sim(r, vol, mode, paths=2000, days=504):
    r = r.to_numpy(); r = r / r.std() * vol / np.sqrt(252)
    r = r - {"full": 0.0, "half": 0.5, "zero": 1.0}[mode] * r.mean()
    out = []
    for _ in range(paths):
        idx = np.concatenate([np.arange(s, s + 10) % len(r) for s in rng.integers(0, len(r), days // 10 + 1)])[:days]
        out.append(run(r[idx] * 50_000.0))
    n = np.array(out); return {"mean": round(float(n.mean())), "p10": round(float(np.percentile(n, 10))), "P(net>0)": round(float((n > 0).mean()), 2)}


out = {"book Sharpe 2023-26": round(float(b.mean() / b.std() * np.sqrt(252)), 2)}
for v in (0.06, 0.10, 0.14, 0.18, 0.24, 0.30):
    out[f"vol {v:.0%}"] = {m: sim(b, v, m) for m in ("full", "half", "zero")}
    out[f"vol {v:.0%}"]["edge value (full - zero)"] = out[f"vol {v:.0%}"]["full"]["mean"] - out[f"vol {v:.0%}"]["zero"]["mean"]
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df_prop2.json").write_text(json.dumps(out, indent=1))

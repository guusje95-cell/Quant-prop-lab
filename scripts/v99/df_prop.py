"""Prop economics of the EXACT daily-flat futures book (DF-1) at a typical flat-by-close firm (0 alpha trials; deployment).
Generic Topstep-like $50k: evaluation target +$3,000, end-of-day trailing max loss $2,000 (trails the highest EOD balance, stops at
the start balance), $49 per evaluation month, $149 activation; funded: same trailing loss, monthly payout of 90% of the profit above
start + $2,000 buffer, account lost -> new evaluation. 2 years, 2,000 paths, 10-day block bootstrap of 2023-26 days; 'half-mean' halves
the mean daily return (live decay). Book scaled to an annual vol of v x $50k. Writes results/v99/df_prop.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
import sys; sys.path.insert(0, str(ROOT / "scripts"))
import fbook

Q = pd.read_parquet(ROOT / "results/v99/df1_sleeves.parquet").drop(columns=["CX4", "CXB"])
b = fbook.build(Q).loc["2023-01-01":"2026-09-30"]; b = b[b.index.weekday < 5]
sw = fbook.build(fbook.sleeves()).loc["2023-01-01":"2026-09-30"]; sw = sw[sw.index.weekday < 5]
rng = np.random.default_rng(7)


def sim(r, vol, half=False, paths=2000, days=504, acct=50_000.0, zero=False):
    r = r.to_numpy(); r = r / r.std() * vol / np.sqrt(252)
    if half:
        r = r - r.mean() / 2
    if zero:
        r = r - r.mean()
    nets = []
    for _ in range(paths):
        idx = np.concatenate([np.arange(s, s + 10) % len(r) for s in rng.integers(0, len(r), days // 10 + 1)])[:days]
        x = r[idx] * acct; net, d = 0.0, 0
        while d < days:
            bal, hi, ok = acct, acct, False; start = d                       # evaluation
            while d < days:
                bal += x[d]; d += 1; hi = max(hi, bal)
                if bal >= acct + 3000: ok = True; break
                if bal <= min(hi, acct + 2000) - 2000: break
            net -= 49 * max(1, (d - start) // 21 + 1)
            if not ok:
                continue
            net -= 149; bal, hi = acct, acct; m0 = d                         # funded
            while d < days:
                bal += x[d]; d += 1; hi = max(hi, bal)
                if bal <= min(hi, acct + 2000) - 2000:
                    break
                if (d - m0) % 21 == 0 and bal > acct + 2000:
                    w = bal - (acct + 2000); net += 0.9 * w; bal -= w; hi = bal
        nets.append(net)
    n = np.array(nets); return {"mean": round(float(n.mean())), "p10": round(float(np.percentile(n, 10))), "P(net>0)": round(float((n > 0).mean()), 2)}


out = {"book Sharpe 2023-26 (daily-flat / swing)": [round(float(b.mean() / b.std() * np.sqrt(252)), 2), round(float(sw.mean() / sw.std() * np.sqrt(252)), 2)]}
for v in (0.10, 0.18, 0.24, 0.30, 0.40):
    out[f"daily-flat vol {v:.0%}"] = {"full": sim(b, v), "half-mean": sim(b, v, True), "ZERO edge (control)": sim(b, v, zero=True)}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/df_prop.json").write_text(json.dumps(out, indent=1))

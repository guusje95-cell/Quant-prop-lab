"""v9.9 R4 (research/v99/r4_protocol.json): the CFD book's index sleeve (P6 + R1 + P1) on the S&P 500 as a 10th sleeve of v9.8, priced as a
Bybit / Hyro tokenized-index perpetual. Writes results/v99/r4_index_sleeve.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
import index_sleeve as IS
COST, FUND = 6.5e-4, 0.04 / (365 * 24)
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z="2026-09-30"):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025")]


def sleeve(symbols):
    pnl = pd.Series(0.0, index=idx)
    for s in symbols:
        x = IS.hourly(s); r = x.close.reindex(idx).ffill(limit=72).pct_change().fillna(0.0)
        dret = r.groupby(r.index.floor("D")).sum(); vol = dret.rolling(20).std() * np.sqrt(252)
        ws = [(0.5 * (0.15 / vol).clip(upper=2.0)).shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0),
              IS._event_leg(x, idx, 13, IS.r1_signal), IS._event_leg(x, idx, 15, IS.p1_signal)]
        for w in ws:
            pnl += w * r - w.diff().abs().fillna(0.0) * COST - w.clip(lower=0) * FUND
    return pnl


s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
b0 = unit(CS.portfolio_v5(V8)[0]); ref = [shp(b0), per(b0)]
out = {"reference v9.8": ref}
for name, syms in (("S&P 500 only (decision)", ["US500"]), ("US100 + US500 (reported only, flagged)", ["US100", "US500"])):
    p = sleeve(syms); b = unit(CS.portfolio_v5(V8.assign(**{"index sleeve": p}))[0]); r = [shp(b), per(b)]
    out[name] = {"sleeve 2022 / 23-24 / 25-26": per(p), "corr with v9.8 (daily)": round(float(dd(p).loc["2022":].corr(dd(b0).loc["2022":])), 3),
                 "book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
    print(name, out[name], flush=True)
out["decision"] = "pass" if out["S&P 500 only (decision)"]["pass"] else "fail"
(ROOT / "results/v99/r4_index_sleeve.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

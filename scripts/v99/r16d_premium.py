"""v9.9 R16d (research/v99/r16d_protocol.json): Coinbase first-hour premium as a filter / size for the R16 short. Writes results/v99/r16d_premium.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import r16_coinbase as R16


def premiums(E):
    H = json.loads((ROOT / "research_data/coinbase_listings/first_hours.json").read_text()); out = {}
    for c, prods in H.items():
        rows = [r for pid, v in prods.items() for r in v if pid.split("-")[-1] in ("USD", "USDC", "USDT")]
        first = [r for r in rows if c in E and pd.Timestamp(r[0]) == E[c]]
        cl, _ = EL._closes(c) if first else (None, None)
        if cl is None:
            continue
        cl = cl.copy(); cl.index = cl.index + pd.Timedelta(hours=1); b = cl.get(E[c] + pd.Timedelta(hours=1))
        if b is not None and np.isfinite(b):
            out[c] = first[0][1] / b - 1
    return out


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx)
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda s: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(V7.assign(**{"listing short": s}))[0]))
    E = R16.events(); P = {c: p for c, p in premiums(E).items() if abs(p) <= 0.5}; Ec = {c: E[c] for c in P}
    hb, ub = R16.trades(Ec, idx, "A"); base = book(s8 + hb)
    hi = {c: t for c, t in Ec.items() if P[c] > 0.005}; lo = {c: t for c, t in Ec.items() if P[c] <= 0.005}
    ha, ua = R16.trades(hi, idx, "A"); hl, ul = R16.trades(lo, idx, "A")
    A = book(s8 + ha); B_ = book(s8 + 1.5 * ha + 0.5 * hl)
    m = lambda u: (len(u), round(float(np.mean([x["trade return %"] for x in u])), 2) if u else None)
    out = {"cleaned events with a premium": len(P), "baseline R16 A (cleaned)": base, "premium > 0.5%: n, mean trade %": m(ua), "premium <= 0.5%: n, mean trade %": m(ul),
           "corr(premium, trade return)": round(float(np.corrcoef([P[x["coin"]] for x in ub], [x["trade return %"] for x in ub])[0, 1]), 3),
           "A premium filter": {"book": A, "pass": bool(A[0] >= base[0] + 0.03 and all(A[1][i] >= base[1][i] for i in range(3)))},
           "B premium sizing": {"book": B_, "pass": bool(B_[0] >= base[0] + 0.03 and all(B_[1][i] >= base[1][i] for i in range(3)))}}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r16d_premium.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

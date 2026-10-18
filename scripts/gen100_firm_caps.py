"""Gen100 part 2: leverage caps and the 5-sleeve swap-free book under firm conditions. Gross notional is measured at the CHALLENGE
size (book at 15% vol x 1.5). When it exceeds the firm's crypto leverage, every position that hour is scaled down to the cap.
Writes results/gen100_caps.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; S = Path(sys.argv[1])
g = {"__file__": str(ROOT / "scripts/gen100_firm_costs.py")}; sys.argv = [sys.argv[0], str(S)]
exec(open(ROOT / "scripts/gen100_firm_costs.py").read().split("ALL = set(CFD)")[0], g)
CS, CFD, POS0, pnl, IDX, ns = g["CS"], g["CFD"], g["POS0"], g["pnl"], g["IDX"], g["ns"]
POS5 = {**POS0, "premium carry": ns["POS"]["premium carry"].reindex(IDX).fillna(0.0), "trend 4h": ns["POS"]["trend 4h"].reindex(IDX).fillna(0.0)}


def run(pos_set, cap=None, scale=1.5, **kw):
    H, P = {}, {}
    for k, p in pos_set.items():
        H[k], P[k] = pnl(p, swap=0.0 if k == "Weiss expiry" else kw["swap"], **{a: b for a, b in kw.items() if a != "swap"})
    H = pd.DataFrame(H).fillna(0.0); ph, W, mult = CS.portfolio_v5(H)
    d = ph.groupby(ph.index.floor("D")).sum().loc["2022":"2026-09-30"]; k15 = 0.15 / (d.std() * np.sqrt(365))
    Wh = W.reindex(IDX.floor("D")).set_axis(IDX); mh = mult.reindex(IDX.floor("D")).set_axis(IDX)
    net = sum(P[k] * Wh[k].to_numpy()[:, None] for k in P).mul(mh * k15 * scale, axis=0)    # net position per coin at challenge size
    gross = net.abs().sum(axis=1).reindex(ph.index)
    by = {k: (P[k].abs().sum(axis=1) * Wh[k] * mh * k15 * scale).reindex(ph.index) for k in P}
    h = ph * k15 * scale
    if cap:
        h = h * (cap / gross).clip(upper=1.0).fillna(1.0)
    d = h.groupby(h.index.floor("D")).sum().loc["2022":"2026-09-30"]
    sh = lambda a, b: float(d.loc[a:b].mean() / d.loc[a:b].std() * np.sqrt(365))
    out = {"Sharpe 2022-26": sh("2022", "2026-09-30"), "TEST": sh("2023", "2024"), "HOLD": sh("2025", "2026-09-30"),
           "ann return at challenge size": float(d.mean() * 365), "hours over cap (%)": float((gross > cap).mean() * 100) if cap else np.nan,
           "gross p99": float(gross.loc["2022":].quantile(0.99)), "gross max": float(gross.loc["2022":].max())}
    out.update({f"max gross {k}": float(v.loc["2022":].max()) for k, v in by.items()})
    return out


ALL = set(CFD); FN = {"BTC", "ETH", "XRP", "ADA", "DOGE", "LINK", "LTC"}; BF = ALL - {"LTC", "DOGE"}
base = dict(spread=(5, 10), comm=0.0, swap=3.3, universe=ALL, weekend_flat=False)
rows = []
for nm, ps, cap, kw in (
        ("3-sleeve CFD book, no cap (Gen90 model)", POS0, None, base),
        ("3-sleeve, cap 1:1 (FundedNext crypto / FTMO Swing as reported)", POS0, 1.0, base),
        ("3-sleeve, cap 1:2", POS0, 2.0, base),
        ("3-sleeve, cap 1:3.3 (FTMO Standard)", POS0, 3.3, base),
        ("3-sleeve, cap 1:5 (BrightFunded as reported)", POS0, 5.0, base),
        ("5-sleeve swap-free book, no cap (Gen90 2.07 model)", POS5, None, {**base, "swap": 0.0}),
        ("5-sleeve swap-free, FundedNext: 6 coins, 5/10 + 4 bp, cap 1:1", POS5, 1.0, {**base, "swap": 0.0, "comm": 4.0, "universe": FN}),
        ("5-sleeve swap-free, FundedNext: 6 coins, 2/5 + 4 bp, cap 1:1", POS5, 1.0, {**base, "swap": 0.0, "comm": 4.0, "universe": FN, "spread": (2, 5)}),
        ("5-sleeve swap-free, FundedNext: 6 coins, 5/10 + 4 bp, cap 1:5 (if BTC/ETH 1:5)", POS5, 5.0, {**base, "swap": 0.0, "comm": 4.0, "universe": FN}),
        ("5-sleeve swap-free, BrightFunded: no LTC/DOGE, 5/10 + 1.2 bp, cap 1:5", POS5, 5.0, {**base, "swap": 0.0, "comm": 1.2, "universe": BF}),
        ("5-sleeve swap-free, BrightFunded: 2/5 + 1.2 bp, cap 1:5", POS5, 5.0, {**base, "swap": 0.0, "comm": 1.2, "universe": BF, "spread": (2, 5)}),
        ("3-sleeve, FTMO eval: 5/10 + 3.25 bp, swap 3.3, cap 1:3.3", POS0, 3.3, {**base, "comm": 3.25}),
        ("3-sleeve, FTMO funded Swing: 5/10 + 3.25, swap 3.3, cap 1:1", POS0, 1.0, {**base, "comm": 3.25}),
        ("3-sleeve, BrightFunded std: 5/10 + 1.2, swap 3.3, cap 1:5", POS0, 5.0, {**base, "comm": 1.2, "universe": BF})):
    r = {"case": nm, **run(ps, cap, **kw)}; rows.append(r)
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen100_caps.csv", index=False)
print("done", flush=True)

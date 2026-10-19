"""Gen88 adoption: CFD books with the Coinbase premium sleeve (Q1). Writes results/gen88_books.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen88_coinbase.py")}
exec(open(ROOT / "scripts/gen88_coinbase.py").read().split("ROWS, CANDS = [], {}")[0], g)
CS, IDX, fhp, d2h, G90, q1, ns = g["CS"], g["IDX"], g["fhp"], g["d2h"], g["G90"], g["q1"], g["ns"]
h3, w = q1(1.0); h0 = fhp(d2h(w), 0.0).reindex(IDX).fillna(0.0)
S0 = ns["sleeves"](0.0, 1.0).reindex(IDX).fillna(0.0)
bb0 = fhp(d2h(CS.delev_bounce_weights().reindex(columns=g["CFD"]).fillna(0.0)), 0.0).reindex(IDX).fillna(0.0)
SF = {**{k: S0[k] for k in ("C*", "premium carry", "trend 4h", "Weiss expiry")}, "delev bounce": bb0}
books = {"CFD book Gen90": G90, "CFD book + Coinbase premium": {**G90, "coinbase premium": h3},
         "swap-free book Gen90": SF, "swap-free book + Coinbase premium": {**SF, "coinbase premium": h0}}
rows = []
for n, cols in books.items():
    ph = CS.portfolio_v5(pd.DataFrame(cols).fillna(0.0))[0]
    d = ph.groupby(ph.index.floor("D")).sum().loc["2022":"2026-09-30"]; x = d * 0.15 / (d.std() * np.sqrt(365))
    eq = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1
    sh = lambda a, b: float(x.loc[a:b].mean() / x.loc[a:b].std() * np.sqrt(365))
    rows.append({"book": n, "Sharpe": sh("2022", "2026"), "TEST": sh("2023", "2024"), "HOLD": sh("2025", "2026"), "MaxDD": float((eq / eq.cummax() - 1).min()),
                 "pos months": float((m > 0).mean()), "CAGR@15%": float(eq.iloc[-1] ** (365 / len(x)) - 1)})
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen88_books.csv", index=False)

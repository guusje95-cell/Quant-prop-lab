"""Gen57 descriptive: C* + BTC leads (perps, real funding) combined with the Binance candidates at equal risk (each sleeve scaled to
10% vol on its own 2023+ history, fixed 50/50 or 1/3 weights, nothing optimised). 2023+ only. Writes results/gen57_combo.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_timing as T
from qpl.lab import binance_pack as B

exec(compile((ROOT / "scripts/gen57_cstar_perp.py").read_text().split("# ---- T10 overlays")[0], "cstar", "exec"))
cstar = run(held, r_perp, F0)                                                          # noqa: F821 (defined by exec)
src = (ROOT / "scripts/gen57_cascade_explore.py").read_text()
ns = {"__name__": "x", "__file__": str(ROOT / "scripts/gen57_cascade_explore.py")}
exec(compile(src.split("allt = sorted")[0].replace("import gen57_cascade_robust as R0", "import gen57_cascade_hourly as R0"), "casc", "exec"), ns)
allt = sorted([t for c in B.coins() for t in ns["trades_full"](c)])
open_ex = []; pnl = {}
for t0, t1, coin, ret in allt:
    open_ex = [e for e in open_ex if e > t0]
    if len(open_ex) >= 3:
        continue
    open_ex.append(t1); d = t1.floor("D"); pnl[d] = pnl.get(d, 0.0) + 0.2 * ret
casc = pd.Series(pnl).sort_index().reindex(pd.date_range("2021-12-01", "2026-09-30")).fillna(0.0)
k = B.k5("ETH"); eth = T.window_pnl(k.close, k.open, k.high, k.low, 21, 23, 1, maker=True)
C = B.coins(); P = B.panel("close", "1D", C); R = P.pct_change(fill_method=None)
F = B.funding_panel(C); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D"); FD = F.groupby(level=0).sum().reindex(P.index)
fs = F.groupby(level=0).sum().reindex(P.index).rolling(7).mean(); listed = P.notna().cumsum() >= 60
rk = (-fs).where(listed).rank(axis=1, pct=True)
w = (rk > 2 / 3).astype(float).div((rk > 2 / 3).sum(axis=1), axis=0) - (rk <= 1 / 3).astype(float).div((rk <= 1 / 3).sum(axis=1), axis=0)
hw = w.fillna(0).shift(1).fillna(0)
carry = (hw * R.fillna(0) - hw * FD.fillna(0)).sum(axis=1) - hw.diff().abs().sum(axis=1) * 5e-4

S = pd.DataFrame({"C*": cstar, "cascade": casc, "ETH evening maker": eth, "funding carry 7d": carry}).loc["2023-01-01":"2026-09-30"].fillna(0.0)
S = S / (S.std() * np.sqrt(365)) * 0.10
print("correlations 2023+:\n", S.corr().round(2))
rows = []
def summ(name, x):
    m = (1 + x).resample("ME").prod() - 1
    dd = (1 + x).cumprod(); dd = (dd / dd.cummax() - 1).min()
    rows.append({"portfolio": name, "sharpe": x.mean() / x.std() * np.sqrt(365), "ann": x.mean() * 365, "pos_months": (m > 0).mean(),
                 "worst_month": m.min(), "maxdd": dd, "worst_day": x.min()})
for c in S:
    summ(c + " alone", S[c])
summ("C* + cascade (50/50)", S[["C*", "cascade"]].mean(axis=1))
summ("C* + funding carry (50/50)", S[["C*", "funding carry 7d"]].mean(axis=1))
summ("C* + ETH evening (50/50)", S[["C*", "ETH evening maker"]].mean(axis=1))
summ("C* + cascade + carry (1/3 each)", S[["C*", "cascade", "funding carry 7d"]].mean(axis=1))
summ("all four (1/4 each)", S.mean(axis=1))
out = pd.DataFrame(rows); out.to_csv(ROOT / "results/gen57_combo.csv", index=False)
print(out.round(3).to_string())

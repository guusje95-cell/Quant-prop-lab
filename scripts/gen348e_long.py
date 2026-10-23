"""Gen348e (FLAGGED post hoc: the long side was seen in Gen348b check 3): long-only premium-discount reversion - Bybit costs, maker,
OKX prices, neighbourhood, by year, correlation with v8.6. Descriptive. Writes results/gen348e.json."""
import json
import numpy as np
import pandas as pd
g = {"__file__": __file__}; src = __import__("pathlib").Path(__file__).resolve().parent.joinpath("gen348b_robust.py").read_text()
exec(compile(src.split("\nP0 = pos(); out =")[0], "gen348b", "exec"), g)
L, pos, pnl, per, cost, FB, R, coins, idx, END = (g[k] for k in ("L", "pos", "pnl", "per", "cost", "FB", "R", "coins", "idx", "END"))
B, X, Hc, pk, ROOT = g["B"], g["X"], g["Hc"], g["pk"], g["ROOT"]
P0 = pos(side=1); out = {"long-only, 5 bp": per(pnl(P0)), "Bybit costs + funding": per(pnl(P0, cost, FB))}
grid = {f"z {th} hold {hd}": per(pnl(pos(th, hd, side=1), cost, FB)) for th in (2.5, 3.0, 3.5) for hd in (2, 4, 6)}
out["neighbourhood (Bybit costs)"] = grid; out["neighbourhood median"] = np.round(np.median(np.array(list(grid.values())), axis=0), 3).tolist()
NM = {"1000PEPE": "PEPE", "1000SHIB": "SHIB"}; ro = {}
for c in coins:
    f = ROOT / f"data/raw/okx/{NM.get(c, c)}-USDT-SWAP_1H.parquet"
    if f.exists():
        x = pd.read_parquet(f)["close"]; x.index = pd.DatetimeIndex(x.index); ro[c] = x.reindex(idx).pct_change(fill_method=None)
RO = pd.DataFrame(ro).reindex(columns=coins); Pm = P0.where(RO.notna(), 0.0)
out["same cells Binance / OKX (5 bp)"] = [per(pnl(Pm)), per(pnl(Pm, ret=RO.fillna(0.0)))]
h = pnl(P0, cost, FB); d = h.groupby(h.index.floor("D")).sum()
out["by year (Bybit costs)"] = {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.loc["2020":END].groupby(d.loc["2020":END].index.year)}
vd = L.V7.groupby(L.V7.index.floor("D")).sum()
out["corr v8.6 daily 2022-26"] = round(float(pd.concat([vd, d], axis=1).loc["2022":END].corr().iloc[0, 1]), 3)
cs = L.H6[["cascade limit strict", "delev bounce"]].groupby(L.H6.index.floor("D")).sum()
out["corr with cascade / delev bounce"] = [round(float(pd.concat([cs.iloc[:, i], d], axis=1).loc["2022":END].corr().iloc[0, 1]), 3) for i in range(2)]
ev = (P0.diff().fillna(P0) > 0); out["entries per year"] = round(float(ev.sum().sum() / 6.75))
print(json.dumps(out, indent=0)); json.dump(out, open(ROOT / "results/gen348e.json", "w"), indent=1)
h.to_frame("premium discount long").to_parquet(ROOT / "results/gen348e_series.parquet")

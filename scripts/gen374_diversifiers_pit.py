"""Gen374 (config/gen374_protocol.json): stress book on today's vs a point-in-time universe, and honest mixes. Writes results/gen374.json.
    cd scripts && python gen374_diversifiers_pit.py <v86 dump parquet>"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
DUMP = sys.argv[1]; sys.argv = sys.argv[:1]
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
exec(open(ROOT / "scripts/gen326_wide_carry.py").read().split("\nimport os\nREF")[0])      # S, H, P, QV, mon, prem(7d), r, F, coins
END = "2026-09-30"
SURV = CS._breadth_universe()
_by = pd.read_csv(ROOT / "research_data/bybit/instruments.csv"); SYM = dict(zip(_by.coin, _by.symbol))
_spr = pd.read_csv(ROOT / "research_data/bybit/spreads.csv").set_index("symbol")["spread_bp_median"]
BCOST = pd.Series({c: 5.5 + 0.5 * float(_spr.get(SYM.get(c, ""), _spr.median())) for c in coins})
Hc = H.loc[:END + " 23:00"]; idx = Hc.index; n = len(idx); R = r.loc[idx]; FH = F.loc[idx]
D = Hc.resample("1D").last(); DR = D.pct_change(fill_method=None)
btc = D["BTC"]; up = btc > btc.rolling(200).mean()                                   # decided at the close of d
uph = up.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(False).astype(float)  # in force during day d+1
upm = up.reindex(D.index).fillna(False).to_numpy()[:, None]
uni_pit = mon.rank(axis=1, ascending=False).le(60).reindex(D.index).fillna(False)
uni_surv = pd.DataFrame(False, index=D.index, columns=coins); uni_surv[SURV] = True; uni_surv = uni_surv & P.reindex(D.index).notna()
PRd = pd.DataFrame({c: S[c][2].resample("1D").mean() for c in coins}).reindex(D.index)
PRh = pd.DataFrame({c: S[c][2][~S[c][2].index.duplicated()] for c in coins}).reindex(idx)
FR = {c: S[c][3].dropna() for c in coins}


def zz(g, w=720):
    return (g - g.rolling(w, min_periods=int(w * 0.7)).mean().shift(1)) / g.rolling(w, min_periods=int(w * 0.7)).std().shift(1)


ZH = zz(PRh)
lp = np.log(Hc); r8 = (lp - lp.shift(8)); sd8 = R.where(Hc.notna()).rolling(720, min_periods=500).std().shift(1) * np.sqrt(8)


def pnl(Pos):
    dE = Pos.diff().fillna(Pos)
    return (Pos * R).sum(axis=1) - (Pos * FH).sum(axis=1) - (dE.abs() * BCOST).sum(axis=1) / 1e4


def devents(mask, hold=3, size=0.1, max_open=8):
    ev = []
    for j, c in enumerate(coins):
        for d in mask.index[mask[c].fillna(False).to_numpy()]:
            ev.append((d, j))
    ev.sort(); Pd = np.zeros((len(D), len(coins))); ends = []; di = {d: i for i, d in enumerate(D.index)}
    for d, j in ev:
        i = di[d]; ends = [e for e in ends if e > i]
        if len(ends) >= max_open:
            continue
        Pd[i:i + hold, j] = size; ends.append(i + hold)
    return pd.DataFrame(Pd, index=D.index, columns=coins).shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)


def book(U):
    Uh = U.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(False)            # universe known at the previous close
    sl = {}
    A = ZH.where(Uh).to_numpy(); Pm = np.zeros((n, len(coins)))
    for j in range(len(coins)):
        z = np.nan_to_num(A[:, j])
        for t in np.flatnonzero(z < -3):
            Pm[t + 1:min(t + 5, n), j] = 0.1 * min(abs(z[t]) / 3, 2)
    sl["premium spike"] = pnl(pd.DataFrame(Pm, index=idx, columns=coins).mul(uph, axis=0))
    sdd = DR.rolling(90, min_periods=60).std().shift(1)
    sl["crash reversal"] = pnl(devents((DR < -3 * sdd) & upm & U, 3, max_open=8))
    ev = []; jx = {c: j for j, c in enumerate(coins)}
    for c in coins:
        for ts in FR[c].index[FR[c] < -0.001]:
            t = idx.get_indexer([ts.floor("h")])[0]
            if t >= 0 and Uh.iat[t, jx[c]]:
                ev.append((t, jx[c]))
    ev.sort(); Pn = np.zeros((n, len(coins))); ends = []
    for t, j in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 5:
            continue
        Pn[t:min(t + 24, n), j] = 0.1; ends.append(t + 24)
    sl["negative funding"] = pnl(pd.DataFrame(Pn, index=idx, columns=coins))
    zd = (PRd - PRd.rolling(90, min_periods=60).mean().shift(1)) / PRd.rolling(90, min_periods=60).std().shift(1)
    sl["daily premium discount"] = pnl(devents((zd < -3) & upm & U, 3))
    bnd = np.flatnonzero(idx.hour % 8 == 7); R8 = r8.where(Uh).to_numpy(); SD8 = sd8.to_numpy(); uu = uph.to_numpy(); ev = []
    for t in bnd:
        if uu[t]:
            ev += [(t, j) for j in np.flatnonzero(np.nan_to_num(R8[t]) < -3 * np.nan_to_num(SD8[t], nan=np.inf))]
    ev.sort(); P8 = np.zeros((n, len(coins))); ends = []
    for t, j in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 8 or t + 1 >= n:
            continue
        P8[t + 1:min(t + 25, n), j] = 0.1; ends.append(t + 24)
    sl["crash 8h"] = pnl(pd.DataFrame(P8, index=idx, columns=coins))
    Dd = pd.DataFrame({k: v.groupby(v.index.floor("D")).sum() for k, v in sl.items()}).loc["2020-01-01":END]
    fit = Dd.loc[:"2024"]; sd = fit.std(); sr = fit.mean() / sd * np.sqrt(365)
    bk = (Dd * (sr.clip(lower=0) / sd)).sum(axis=1); bk = bk * 0.15 / (bk.loc[:"2024"].std() * np.sqrt(365))
    return bk, Dd


sh = lambda d, a, z: round(float(d.loc[a:z].mean() / d.loc[a:z].std() * np.sqrt(365)), 3)
per = lambda d: [sh(d, "2020", "2022"), sh(d, "2023", "2024"), sh(d, "2025", END)]
out = {}; BK = {}
for nm, U in (("S today's 60 coins", uni_surv), ("P point-in-time top-60", uni_pit)):
    bk, Dd = book(U); BK[nm] = bk
    out[nm] = {"book 2020-22 / 2023-24 / 2025-26": per(bk), "2020-24": sh(bk, "2020", "2024"), "2020-26": sh(bk, "2020", END),
               "expected live (0.6 x 2020-26)": round(0.6 * sh(bk, "2020", END), 3), "sleeves 2020-22 / 2023-24 / 2025-26": {k: per(Dd[k]) for k in Dd}}
    print(nm, json.dumps(out[nm]), flush=True)
s, p = out["S today's 60 coins"], out["P point-in-time top-60"]
out["stress book kept"] = bool(p["2020-24"] >= 0.7 * s["2020-24"] and p["expected live (0.6 x 2020-26)"] >= 0.8)
# honest crypto books (Gen372) and mixes, 2022-26 daily
H0 = pd.read_parquet(DUMP).drop(columns="port").loc[:END + " 23:00"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
F0 = dd(CS.portfolio_v5(H0.drop(columns="premium carry 60"))[0]); F2 = dd(CS.portfolio_v5(H0.drop(columns=["premium carry 60", "premium carry"]))[0])
fut = pd.read_parquet(ROOT / "results/futures_book_rebuild.parquet")["book"]; fut.index = pd.DatetimeIndex(fut.index).normalize()
X_ = pd.concat({"F0": F0, "F2": F2, "stress P": BK["P point-in-time top-60"], "futures": fut}, axis=1).loc["2022-01-01":END]
X_["futures"] = X_["futures"].fillna(0.0)                                             # weekends: no futures P&L
X_ = X_.dropna(); Xs = X_ / X_.std()
out["2022-26 Sharpe each"] = {k: sh(X_[k], "2022", END) for k in X_}
out["2022-26 daily corr"] = X_.corr().round(3).to_dict()
mixes = {}
for base in ("F0", "F2"):
    for add in (["stress P"], ["futures"], ["stress P", "futures"]):
        best = max(((w, sh(Xs[base] + sum(w * Xs[a] for a in add), "2022", END)) for w in np.arange(0, 1.51, 0.05)), key=lambda t: t[1])
        mixes[f"{base} + {' + '.join(add)}"] = {"equal risk": sh(Xs[base] + sum(Xs[a] for a in add), "2022", END), "best weight (in-sample, optimistic)": [round(best[0], 2), best[1]]}
out["mixes 2022-26 (backtest Sharpe; base alone: F0 %.3f, F2 %.3f)" % (sh(X_["F0"], "2022", END), sh(X_["F2"], "2022", END))] = mixes
(ROOT / "results/gen374.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

"""Gen368 (config/gen368_protocol.json). Writes results/gen368.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
from qpl.lab import propfirms as PF
_a = {"__file__": __file__}; exec(compile(open(SB.ROOT / "scripts/gen364_reversal.py").read().split("\nT = {")[0], "g364", "exec"), _a)
_b = {"__file__": __file__}; exec(compile(open(SB.ROOT / "scripts/gen365_crash8h.py").read().split("\ndef book(")[0], "g365", "exec"), _b)
_c = {"__file__": __file__}; exec(compile(open(SB.ROOT / "scripts/gen363_union.py").read().split("\ndef book(")[0], "g363", "exec"), _c)
coins, idx, n, D = SB.coins, SB.idx, SB.n, SB.D
up = (D["BTC"] > D["BTC"].rolling(200).mean()); upf = up.reindex(idx.floor("D")).set_axis(idx).fillna(False).astype(float)


def sleeves(cost_mult=1.0, ret=None):
    b0, r0 = SB.BCOST.copy(), SB.R; SB.BCOST = SB.BCOST * cost_mult
    if ret is not None:
        SB.R = ret
    try:
        Z = SB.premium_z(); A = Z.reindex(columns=coins).to_numpy(); P = np.zeros((n, len(coins)))
        for j in range(len(coins)):
            z = np.nan_to_num(A[:, j])
            for t in np.flatnonzero(z < -3):
                P[t + 1:min(t + 5, n), j] = 0.1 * min(abs(z[t]) / 3, 2)
        ps = SB.pnl(pd.DataFrame(P, index=idx, columns=coins).mul(upf, axis=0), maker=True)
        sdd = SB.DR.rolling(90, min_periods=60).std().shift(1); mask = (SB.DR < -3 * sdd) & up.reindex(D.index).fillna(False).to_numpy()[:, None]
        cr = SB.pnl(SB.daily_event_positions(mask, 1.0, 3, max_open=8), maker=True)
        ev = set()
        for j, c in enumerate(coins):
            for src in (SB.FUND_RAW.get(c), SB.BYB_RAW.get(c)):
                if src is not None:
                    f = src.dropna()
                    for ts in f.index[f < -0.001]:
                        t = idx.get_indexer([ts.floor("h")])[0]
                        if t >= 0:
                            ev.add((t, j))
        P = np.zeros((n, len(coins))); ends = []
        for t, j in sorted(ev):
            if P[t, j] > 0:
                continue
            ends = [e for e in ends if e > t]
            if len(ends) >= 5:
                continue
            P[t:min(t + 24, n), j] = 0.1; ends.append(t + 24)
        nf = SB.pnl(pd.DataFrame(P, index=idx, columns=coins), maker=True)
        return {"premium spike": ps, "crash reversal": cr, "negative funding": nf, "daily premium discount": _a["disc"](), "crash 8h": _b["pos"]()}
    finally:
        SB.BCOST, SB.R = b0, r0


def c2_hourly(S):
    Dd = pd.DataFrame({k: SB.daily(v) for k, v in S.items()}).fillna(0.0); fit = Dd.loc[:"2024"]; sd = fit.std(); sr = fit.mean() / sd * np.sqrt(365)
    w = sr.clip(lower=0) / sd; h = sum(S[k] * w[k] for k in S); bd = SB.daily(h)
    return h * 0.15 / (bd.loc[:"2024"].std() * np.sqrt(365))


out = {}
S = sleeves(); hb = c2_hourly(S); bd = SB.daily(hb); out["1 rebuild"] = SB.evaluate(bd)
ref = pd.read_parquet(SB.ROOT / "results/gen366_book.parquet").iloc[:, 0]; out["1 max diff vs Gen366 (daily)"] = float((bd - ref.reindex(bd.index)).abs().max())
out["2 costs x2 expected live"] = SB.evaluate(SB.daily(c2_hourly(sleeves(2.0))))["EXPECTED LIVE (0.6 x 2020-26)"]
out["3 tail"] = {"worst day": round(float(bd.min()), 4), "worst hour": round(float(hb.min()), 4), "max drawdown": round(float(((1 + bd).cumprod() / (1 + bd).cumprod().cummax() - 1).min()), 3)}
print(json.dumps(out, indent=0), flush=True)
v = pd.read_parquet(SB.ROOT / "results/cache_v86_final.parquet")["portfolio"].loc["2022-01-01":SB.END + " 23:00"]
hb22 = hb.reindex(v.index).fillna(0.0)
src = open(SB.ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
HY = PF.PRESETS["HyroTrader Two-Step $200k"]


def unit(h):
    d = h.groupby(h.index.floor("D")).sum(); return h * 0.15 / (d.loc[:"2024"].std() * np.sqrt(365))


def shift_to(h, target):
    d = h.groupby(h.index.floor("D")).sum(); return h - (d.mean() - target * d.std() / np.sqrt(365)) / 24


vu, bu = unit(v), unit(hb22)
dsh = lambda h: (lambda d: float(d.mean() / d.std() * np.sqrt(365)))(h.groupby(h.index.floor("D")).sum())
res = {}
for lvl in ("backtest", "planning"):
    va = vu if lvl == "backtest" else shift_to(vu, 1.78); ba = bu if lvl == "backtest" else shift_to(bu, 0.6 * dsh(bu))
    for nm, h in (("v8.6 alone", va), ("v8.6 + 0.65 x stress book", unit(va + 0.65 * ba))):
        x = h.loc["2025-01-01":]
        pb = PF.pipeline(to_daily_stop(x * 2.0, 0.025), HY, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.025), horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
        res[f"{lvl}: {nm}"] = {"Sharpe 2022-26": round(dsh(h), 3), "net 2y": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3),
                               "days to funded": pb["days_to_funded_median"]}
        print(lvl, nm, res[f"{lvl}: {nm}"], flush=True)
out["4 prop (HyroTrader $200k, 2025-26 bootstrap)"] = res
json.dump(out, open(SB.ROOT / "results/gen368.json", "w"), indent=1); hb.to_frame("stress book").to_parquet(SB.ROOT / "results/gen368_book_hourly.parquet")

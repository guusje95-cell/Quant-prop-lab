"""Gen362 (config/gen362_protocol.json). Writes results/gen362.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
_g = {"__file__": __file__}; exec(compile(open(SB.ROOT / "scripts/gen361_refine.py").read().split("\ns24 = lambda")[0], "gen361", "exec"), _g)
nf, cr, ps = _g["nf"], _g["cr"], _g["ps"]
coins, idx, n, D, DR = SB.coins, SB.idx, SB.n, SB.D, SB.DR
up = (D["BTC"] > D["BTC"].rolling(200).mean())
upm = up.reindex(D.index).fillna(False).to_numpy()[:, None]
book = pd.read_parquet(SB.ROOT / "results/gen361_book.parquet").iloc[:, 0]; v = SB.v86_daily(); out = {}


def wkcr(k=3.0, hold=7, lag=0):
    r7 = D / D.shift(7) - 1; sd7 = DR.rolling(90, min_periods=60).std().shift(1) * np.sqrt(7)
    P = SB.daily_event_positions((r7 < -k * sd7) & upm, 1.0, hold); return SB.pnl(P.shift(24 * lag).fillna(0.0), maker=True)


def rescr(k=3.0, lag=0):
    beta = DR.rolling(60, min_periods=50).cov(DR["BTC"]).div(DR["BTC"].rolling(60, min_periods=50).var(), axis=0).shift(1)
    res = DR - beta.mul(DR["BTC"], axis=0); rsd = res.rolling(90, min_periods=60).std().shift(1)
    mask = (res < -k * rsd) & upm; mask["BTC"] = False
    Pc = SB.daily_event_positions(mask, 1.0, 3); bh = beta.reindex(idx.floor("D")).set_axis(idx).ffill()
    Pc["BTC"] = Pc["BTC"] - (Pc.drop(columns=["BTC"]) * bh.drop(columns=["BTC"]).fillna(1.0)).sum(axis=1)
    return SB.pnl(Pc.shift(24 * lag).fillna(0.0), maker=True)


T = {"A weekly crash reversal": wkcr, "B residual crash reversal + BTC filter": rescr}; passed = {}
for nm, fn in T.items():
    h = fn(); d = SB.daily(h); s = SB.periods(d)
    c1 = float(pd.concat([d, v], axis=1).loc["2022":SB.END].corr().iloc[0, 1]); c2 = float(pd.concat([d, book], axis=1).loc["2020":SB.END].corr().iloc[0, 1])
    ok = bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c1) <= 0.2 and abs(c2) <= 0.5)
    r = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c1, 3), "corr book": round(c2, 3), "entry bar": ok}
    if ok:
        nb = [SB.periods(SB.daily(fn(k))) for k in (2.5, 3.5)]; lat = SB.periods(SB.daily(fn(lag=1)))
        r["robustness"] = {"k 2.5 / 3.5": nb, "one day later": lat}
        r["robust"] = bool(all(min(x) > 0 for x in nb) and min(lat) > 0)
        if r["robust"]:
            passed[nm] = h
    out[nm] = r; print(nm, r, flush=True)
cur = {"premium spike": ps("z", 4), "crash reversal": cr(8), "negative funding": nf(5)}
s24 = lambda S: SB.sh(SB.build(S), "2020", "2024")
upf = up.reindex(idx.floor("D")).set_axis(idx).fillna(False).astype(float)


def filtered(h_unf, P_builder):
    return h_unf


# F1 / F2: rebuild with positions zeroed when BTC < 200d (positions of the existing sleeves)
Z = SB.premium_z(); A = Z.reindex(columns=coins).to_numpy(); P = np.zeros((n, len(coins)))
for j in range(len(coins)):
    z = np.nan_to_num(A[:, j])
    for t in np.flatnonzero(z < -3):
        P[t + 1:min(t + 5, n), j] = 0.1 * min(abs(z[t]) / 3, 2)
Pps = pd.DataFrame(P, index=idx, columns=coins)
ps_f = SB.pnl(Pps.mul(upf, axis=0), maker=True)
o1 = s24(cur); o2 = s24({**cur, "premium spike": ps_f}); out["F1 premium spike BTC filter (2020-24 no / yes)"] = [round(o1, 3), round(o2, 3)]
if o2 > o1:
    cur["premium spike"] = ps_f
ev = []
for j, c in enumerate(coins):
    f = SB.FUND_RAW[c].dropna()
    for ts in f.index[f < -0.001]:
        t = idx.get_indexer([ts.floor("h")])[0]
        if t >= 0:
            ev.append((t, j))
ev.sort(); P = np.zeros((n, len(coins))); ends = []
for t, j in ev:
    ends = [e for e in ends if e > t]
    if len(ends) >= 5:
        continue
    P[t:min(t + 24, n), j] = 0.1; ends.append(t + 24)
nf_f = SB.pnl(pd.DataFrame(P, index=idx, columns=coins).mul(upf, axis=0), maker=True)
o1 = s24(cur); o2 = s24({**cur, "negative funding": nf_f}); out["F2 negative funding BTC filter (2020-24 no / yes)"] = [round(o1, 3), round(o2, 3)]
if o2 > o1:
    cur["negative funding"] = nf_f
for nm, h in passed.items():
    o1 = s24(cur); o2 = s24({**cur, nm: h}); out[f"F3 add {nm} (2020-24 no / yes)"] = [round(o1, 3), round(o2, 3)]
    if o2 > o1:
        cur[nm] = h
bk = SB.build(cur); out["BOOK v3"] = SB.evaluate(bk); out["BOOK v3"]["sleeves"] = list(cur)
print(json.dumps({k: out[k] for k in out if k.startswith(("F", "BOOK"))}, indent=0))
bk.to_frame("stress book v3").to_parquet(SB.ROOT / "results/gen362_book.parquet")
pd.DataFrame({k: SB.daily(x) for k, x in cur.items()}).to_parquet(SB.ROOT / "results/gen362_sleeves.parquet")
json.dump(out, open(SB.ROOT / "results/gen362.json", "w"), indent=1)

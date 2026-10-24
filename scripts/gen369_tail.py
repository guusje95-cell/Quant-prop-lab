"""Gen369 (config/gen369_protocol.json). Writes results/gen369.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
from qpl.lab import propfirms as PF
from qpl.lab import binance_pack as B, extra_pack as X
coins, idx, n, D, DR, pk = SB.coins, SB.idx, SB.n, SB.D, SB.DR, SB.pk
up = (D["BTC"] > D["BTC"].rolling(200).mean()); upf = up.reindex(idx.floor("D")).set_axis(idx).fillna(False).astype(float)
updd = up.reindex(D.index).fillna(False).to_numpy()[:, None]; uph = up.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(False).to_numpy()
Z = SB.premium_z(); A = Z.reindex(columns=coins).to_numpy(); trig = (A < -3)
btcz = SB.zz(SB.R["BTC"].where(SB.Hc["BTC"].notna())).to_numpy(); crowd = np.nan_to_num(trig).sum(axis=1) >= 5
systemic = (np.nan_to_num(btcz) < -3) | crowd


def P_ps(filt):
    P = np.zeros((n, len(coins)))
    for j in range(len(coins)):
        z = np.nan_to_num(A[:, j])
        for t in np.flatnonzero(z < -3):
            if filt and systemic[t]:
                continue
            P[t + 1:min(t + 5, n), j] = 0.1 * min(abs(z[t]) / 3, 2)
    return pd.DataFrame(P, index=idx, columns=coins).mul(upf, axis=0)


def P_cr():
    sdd = DR.rolling(90, min_periods=60).std().shift(1); return SB.daily_event_positions((DR < -3 * sdd) & updd, 1.0, 3, max_open=8)


def P_nf():
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
    return pd.DataFrame(P, index=idx, columns=coins)


prem = {}
for c in coins:
    p = (B.premium(c)["close"] if c in pk else X.premium(c)); p = p[~p.index.duplicated()]; p.index = pd.DatetimeIndex(p.index); prem[c] = p.resample("1D").mean()
PR = pd.DataFrame(prem).reindex(index=D.index, columns=coins)


def P_disc():
    z = (PR - PR.rolling(90, min_periods=60).mean().shift(1)) / PR.rolling(90, min_periods=60).std().shift(1)
    return SB.daily_event_positions((z < -3) & updd, 1.0, 3)


lp = np.log(SB.Hc); r8 = (lp - lp.shift(8)).to_numpy(); hsd = SB.R.where(SB.Hc.notna()).rolling(720, min_periods=500).std().shift(1).to_numpy() * np.sqrt(8)


def P_c8(filt):
    ev = []
    for t in np.flatnonzero(idx.hour % 8 == 7):
        if uph[t] and not (filt and systemic[t]):
            ev += [(t, j) for j in np.flatnonzero(np.nan_to_num(r8[t]) < -3 * np.nan_to_num(hsd[t], nan=np.inf))]
    P = np.zeros((n, len(coins))); ends = []
    for t, j in sorted(ev):
        ends = [e for e in ends if e > t]
        if len(ends) >= 8 or t + 1 >= n:
            continue
        P[t + 1:min(t + 25, n), j] = 0.1; ends.append(t + 24)
    return pd.DataFrame(P, index=idx, columns=coins)


def book_positions(filt=False):
    Ps = {"premium spike": P_ps(filt), "crash reversal": P_cr(), "negative funding": P_nf(), "daily premium discount": P_disc(), "crash 8h": P_c8(filt)}
    Dd = pd.DataFrame({k: SB.daily(SB.pnl(v, maker=True)) for k, v in Ps.items()}).fillna(0.0); fit = Dd.loc[:"2024"]; sd = fit.std(); sr = fit.mean() / sd * np.sqrt(365)
    w = sr.clip(lower=0) / sd; Pb = sum(Ps[k] * w[k] for k in Ps); h = SB.pnl(Pb, maker=True); sc = 0.15 / (SB.daily(h).loc[:"2024"].std() * np.sqrt(365))
    return Pb * sc


def cap(Pb, c=0.15):
    g = Pb.abs().sum(axis=1); return Pb.mul((c / g).clip(upper=1.0).fillna(1.0), axis=0)


LO, _ = SB.lohi()


def stop(Pb, s=0.04):
    P = Pb.to_numpy().copy(); C = SB.Hc.to_numpy(); Lw = LO.to_numpy(); entry = np.full(P.shape[1], np.nan); extra = np.zeros(n); dead = np.zeros(P.shape[1], bool)
    for t in range(1, n):
        for j in np.flatnonzero((P[t] != 0) | (P[t - 1] != 0)):
            if P[t - 1, j] == 0 and P[t, j] != 0:
                entry[j] = C[t - 1, j]; dead[j] = False
            if P[t, j] == 0:
                entry[j] = np.nan; dead[j] = False; continue
            if dead[j]:
                P[t, j] = 0.0; continue
            if np.isfinite(entry[j]) and np.isfinite(Lw[t, j]) and Lw[t, j] <= entry[j] * (1 - s):
                px = entry[j] * (1 - s) * (1 - 1e-3); extra[t] += P[t, j] * (px / C[t - 1, j] - 1) - P[t, j] * 5.5e-4; P[t, j] = 0.0; dead[j] = True
    return pd.DataFrame(P, index=Pb.index, columns=Pb.columns), pd.Series(extra, index=Pb.index)


base = book_positions(False); filt = book_positions(True)
O = {"T0": (base, None), "T1": (filt, None), "T2": (cap(base), None)}
Ps3, ex3 = stop(base); O["T3"] = (Ps3, ex3); O["T4"] = (cap(filt), None)
v = pd.read_parquet(SB.ROOT / "results/cache_v86_final.parquet")["portfolio"].loc["2022-01-01":SB.END + " 23:00"]
src = open(SB.ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
dsh = lambda h: (lambda d: float(d.mean() / d.std() * np.sqrt(365)))(h.groupby(h.index.floor("D")).sum())
unit = lambda h, a="2022-01-01", z="2024-12-31 23:00": h * 0.15 / (h.loc[a:z].groupby(h.loc[a:z].index.floor("D")).sum().std() * np.sqrt(365))
shift_to = lambda h, tg: h - (h.groupby(h.index.floor("D")).sum().mean() - tg * h.groupby(h.index.floor("D")).sum().std() / np.sqrt(365)) / 24


def prop(h, a, z):
    x = h.loc[a:z]; pb = PF.pipeline(to_daily_stop(x * 2.0, 0.025), HY, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.025), horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}


out = {}; vu = unit(v)
for k, (Pb, ex) in O.items():
    hb = SB.pnl(Pb, maker=True) + (ex if ex is not None else 0.0); hb = hb.reindex(v.index).fillna(0.0)
    acct = unit(vu + 0.65 * unit(hb))
    out[k] = {"book": SB.evaluate(SB.daily(SB.pnl(Pb, maker=True) + (ex if ex is not None else 0.0))), "worst hour book": round(float(hb.min()), 4),
              "account Sharpe 2022-26": round(dsh(acct), 3), "prop 2022-24": prop(acct, "2022-01-01", "2024-12-31 23:00")}
    print(k, out[k]["book"]["EXPECTED LIVE (0.6 x 2020-26)"], out[k]["worst hour book"], out[k]["prop 2022-24"], flush=True)
out["prop 2022-24, v8.6 alone"] = prop(vu, "2022-01-01", "2024-12-31 23:00")
ok = {k: out[k]["prop 2022-24"]["net"] for k in O if out[k]["prop 2022-24"]["P_profit"] >= 0.9}
ch = max(ok, key=ok.get) if ok else max(O, key=lambda k: out[k]["prop 2022-24"]["net"]); out["chosen"] = ch
Pb, ex = O[ch]; hb = (SB.pnl(Pb, maker=True) + (ex if ex is not None else 0.0)).reindex(v.index).fillna(0.0)
for lvl in ("backtest", "planning"):
    va = vu if lvl == "backtest" else shift_to(vu, 1.78); ba = unit(hb) if lvl == "backtest" else shift_to(unit(hb), 0.6 * dsh(unit(hb)))
    for nm, h in (("v8.6 alone", va), ("v8.6 + 0.65 x book", unit(va + 0.65 * ba))):
        out[f"2025-26 {lvl}: {nm}"] = {"Sharpe": round(dsh(h), 3), **prop(h, "2025-01-01", SB.END + " 23:00")}; print(lvl, nm, out[f"2025-26 {lvl}: {nm}"], flush=True)
json.dump(out, open(SB.ROOT / "results/gen369.json", "w"), indent=1)
pd.DataFrame({"book": hb}).to_parquet(SB.ROOT / "results/gen369_book_hourly.parquet")

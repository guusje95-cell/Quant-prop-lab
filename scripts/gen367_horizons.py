"""Gen367 (config/gen367_protocol.json). Writes results/gen367.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
coins, idx, n, D, DR = SB.coins, SB.idx, SB.n, SB.D, SB.DR
upd = (D["BTC"] > D["BTC"].rolling(200).mean()).shift(1); uph = upd.reindex(idx.floor("D")).set_axis(idx).fillna(False).to_numpy()
updd = (D["BTC"] > D["BTC"].rolling(200).mean()).reindex(D.index).fillna(False).to_numpy()[:, None]
S5 = pd.read_parquet(SB.ROOT / "results/gen366_sleeves.parquet").fillna(0.0); book0 = pd.read_parquet(SB.ROOT / "results/gen366_book.parquet").iloc[:, 0]
lp = np.log(SB.Hc); hsd = SB.R.where(SB.Hc.notna()).rolling(720, min_periods=500).std().shift(1).to_numpy()


def hcr(k=3.0, lag=0, L=4, hold=12):
    rL = (lp - lp.shift(L)).to_numpy(); sd = hsd * np.sqrt(L); bnd = np.flatnonzero(idx.hour % L == L - 1); ev = []
    for t in bnd:
        if uph[t]:
            ev += [(t, j) for j in np.flatnonzero(np.nan_to_num(rL[t]) < -k * np.nan_to_num(sd[t], nan=np.inf))]
    ev.sort(); P = np.zeros((n, len(coins))); ends = []
    for t, j in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 8 or t + 1 + lag >= n:
            continue
        P[t + 1 + lag:min(t + 1 + hold + lag, n), j] = 0.1; ends.append(t + hold + lag)
    return SB.pnl(pd.DataFrame(P, index=idx, columns=coins), maker=True)


def dcr3(k=3.0, lag=0):
    r3 = D / D.shift(3) - 1; sd3 = DR.rolling(90, min_periods=60).std().shift(1) * np.sqrt(3)
    P = SB.daily_event_positions((r3 < -k * sd3) & updd, 1.0, 5); return SB.pnl(P.shift(24 * lag).fillna(0.0), maker=True)


def c2(Sx):
    fit = Sx.loc[:"2024"]; sd = fit.std(); sr = fit.mean() / sd * np.sqrt(365); bk = (Sx * (sr.clip(lower=0) / sd)).sum(axis=1)
    return bk * 0.15 / (bk.loc[:"2024"].std() * np.sqrt(365))


v = SB.v86_daily(); out = {}; S = S5.copy()
for nm, fn in (("A 4-hour crash reversal", hcr), ("B 3-day crash reversal", dcr3)):
    d = SB.daily(fn()); s = SB.periods(d)
    c1 = float(pd.concat([d, v], axis=1, sort=True).loc["2022":SB.END].corr().iloc[0, 1]); cb = float(pd.concat([d, book0], axis=1, sort=True).loc["2020":SB.END].corr().iloc[0, 1])
    ok = bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c1) <= 0.2 and abs(cb) <= 0.5)
    r = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c1, 3), "corr book": round(cb, 3), "entry bar": ok}
    if ok:
        rb = [SB.periods(SB.daily(fn(2.5))), SB.periods(SB.daily(fn(3.5))), SB.periods(SB.daily(fn(lag=1)))]; r["robustness"] = rb; r["robust"] = bool(all(min(x) > 0 for x in rb))
        if r["robust"]:
            S1 = pd.concat([S, d.rename(nm)], axis=1, sort=True).fillna(0.0).loc["2020-01-01":SB.END]
            a, b = SB.sh(c2(S), "2020", "2024"), SB.sh(c2(S1), "2020", "2024"); r["C2 book 2020-24 without / with"] = [round(a, 3), round(b, 3)]
            if b > a:
                S = S1; r["added"] = True
    out[nm] = r; print(nm, r, flush=True)
bk = c2(S); out["BOOK"] = SB.evaluate(bk); out["BOOK"]["sleeves"] = list(S.columns)
rho = float(pd.concat([v.loc["2022":SB.END], bk], axis=1, sort=True).loc["2022":SB.END].corr().iloc[0, 1]); sb = out["BOOK"]["EXPECTED LIVE (0.6 x 2020-26)"]
mix = lambda q: (1.78 + q * sb) / np.sqrt(1 + q * q + 2 * q * rho); bw = float(max(np.arange(0, 2.01, 0.05), key=mix)); out["mix with v8.6"] = {"corr": round(rho, 3), "best weight": round(bw, 2), "best": round(mix(bw), 3)}
print(json.dumps({"BOOK": out["BOOK"], "mix": out["mix with v8.6"]}, indent=0))
json.dump(out, open(SB.ROOT / "results/gen367.json", "w"), indent=1); S.to_parquet(SB.ROOT / "results/gen367_sleeves.parquet"); bk.to_frame("stress book").to_parquet(SB.ROOT / "results/gen367_book.parquet")

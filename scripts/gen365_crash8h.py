"""Gen365 (config/gen365_protocol.json). Writes results/gen365.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
coins, idx, n, D = SB.coins, SB.idx, SB.n, SB.D
upd = (D["BTC"] > D["BTC"].rolling(200).mean()).shift(1); uph = upd.reindex(idx.floor("D")).set_axis(idx).fillna(False).to_numpy()
S0 = pd.read_parquet(SB.ROOT / "results/gen364_sleeves.parquet").fillna(0.0); book0 = pd.read_parquet(SB.ROOT / "results/gen364_book.parquet").iloc[:, 0]
lp = np.log(SB.Hc); r8 = (lp - lp.shift(8)).to_numpy(); sd = SB.R.where(SB.Hc.notna()).rolling(720, min_periods=500).std().shift(1).to_numpy() * np.sqrt(8)
bnd = np.flatnonzero(idx.hour % 8 == 7)                                    # bars 07/15/23 close at 08/16/00


def pos(k=3.0, lag=0):
    ev = []
    for t in bnd:
        if not uph[t]:
            continue
        hit = np.flatnonzero(np.nan_to_num(r8[t]) < -k * np.nan_to_num(sd[t], nan=np.inf))
        ev += [(t, j) for j in hit]
    ev.sort(); P = np.zeros((n, len(coins))); ends = []
    for t, j in ev:
        ends = [e for e in ends if e > t]
        if len(ends) >= 8 or t + 1 + lag >= n:
            continue
        P[t + 1 + lag:min(t + 25 + lag, n), j] = 0.1; ends.append(t + 24 + lag)
    return SB.pnl(pd.DataFrame(P, index=idx, columns=coins), maker=True)


def book(Dd):
    bk = (Dd / Dd.loc[:"2024"].std()).sum(axis=1); return bk * 0.15 / (bk.loc[:"2024"].std() * np.sqrt(365))


h = pos(); d = SB.daily(h); s = SB.periods(d); v = SB.v86_daily()
c1 = float(pd.concat([d, v], axis=1, sort=True).loc["2022":SB.END].corr().iloc[0, 1]); c2 = float(pd.concat([d, book0], axis=1, sort=True).loc["2020":SB.END].corr().iloc[0, 1])
cc = float(pd.concat([d, S0["crash reversal"]], axis=1, sort=True).loc["2020":SB.END].corr().iloc[0, 1])
ok = bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c1) <= 0.2 and abs(c2) <= 0.5)
out = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c1, 3), "corr book": round(c2, 3), "corr daily crash reversal": round(cc, 3), "entry bar": ok}
S = S0
if ok:
    rb = [SB.periods(SB.daily(pos(2.5))), SB.periods(SB.daily(pos(3.5))), SB.periods(SB.daily(pos(lag=1)))]
    out["robustness"] = rb; out["robust"] = bool(all(min(x) > 0 for x in rb))
    if out["robust"]:
        b1 = book(pd.concat([S0, d.rename("crash 8h")], axis=1, sort=True).fillna(0.0))
        out["book 2020-24 without / with"] = [round(SB.sh(book(S0), "2020", "2024"), 3), round(SB.sh(b1, "2020", "2024"), 3)]
        if SB.sh(b1, "2020", "2024") > SB.sh(book(S0), "2020", "2024"):
            S = pd.concat([S0, d.rename("crash 8h")], axis=1, sort=True).fillna(0.0); out["added"] = True
bk = book(S); out["BOOK"] = SB.evaluate(bk); out["BOOK"]["sleeves"] = list(S.columns)
rho = float(pd.concat([v.loc["2022":SB.END], bk], axis=1, sort=True).loc["2022":SB.END].corr().iloc[0, 1]); sb = out["BOOK"]["EXPECTED LIVE (0.6 x 2020-26)"]
mix = lambda w: (1.78 + w * sb) / np.sqrt(1 + w * w + 2 * w * rho); bw = float(max(np.arange(0, 2.01, 0.05), key=mix)); out["mix with v8.6"] = {"best weight": round(bw, 2), "best": round(mix(bw), 3)}
print(json.dumps(out, indent=0)); json.dump(out, open(SB.ROOT / "results/gen365.json", "w"), indent=1)
S.to_parquet(SB.ROOT / "results/gen365_sleeves.parquet"); bk.to_frame("stress book").to_parquet(SB.ROOT / "results/gen365_book.parquet")

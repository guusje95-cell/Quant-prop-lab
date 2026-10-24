"""Gen364 (config/gen364_protocol.json). Writes results/gen364.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
from qpl.lab import binance_pack as B
coins, idx, n, D, DR, pk = SB.coins, SB.idx, SB.n, SB.D, SB.DR, SB.pk
up = (D["BTC"] > D["BTC"].rolling(200).mean()).reindex(D.index).fillna(False).to_numpy()[:, None]
S0 = pd.read_parquet(SB.ROOT / "results/gen363_sleeves.parquet").fillna(0.0); book0 = pd.read_parquet(SB.ROOT / "results/gen363_book.parquet").iloc[:, 0]
v = SB.v86_daily()
OI = {}
for c in coins:
    if c in ("BTC", "ETH"):
        continue
    if c in pk:
        o = B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1h").last()
    else:
        o = pd.read_parquet(SB.ROOT / f"research_data/binance_extra/{c}USDT_oi_1h.parquet")["oi_value"]; o.index = pd.DatetimeIndex(o.index); o = o[~o.index.duplicated()]
    od = o.resample("1D").last(); OI[c] = od
OI = pd.DataFrame(OI).reindex(index=D.index, columns=coins)


def delev(th=0.15, hold=2, lag=0):
    m = ((OI / OI.shift(1) - 1) < -th) & (DR < 0) & up
    return SB.pnl(SB.daily_event_positions(m, 1.0, hold).shift(24 * lag).fillna(0.0), maker=True)


Z = SB.premium_z(); pdm = Z.copy()                                     # hourly premium z -> use the raw premium daily mean instead
from qpl.lab import extra_pack as X
prem = {}
for c in coins:
    p = (B.premium(c)["close"] if c in pk else X.premium(c)); p = p[~p.index.duplicated()]; p.index = pd.DatetimeIndex(p.index); prem[c] = p.resample("1D").mean()
PR = pd.DataFrame(prem).reindex(index=D.index, columns=coins)


def disc(k=3.0, hold=3, lag=0):
    z = (PR - PR.rolling(90, min_periods=60).mean().shift(1)) / PR.rolling(90, min_periods=60).std().shift(1)
    return SB.pnl(SB.daily_event_positions((z < -k) & up, 1.0, hold).shift(24 * lag).fillna(0.0), maker=True)


T = {"A altcoin delev bounce + BTC filter": (delev, (0.10, 0.20)), "B daily premium discount + BTC filter": (disc, (2.5, 3.5))}
out = {}; S = S0.copy()


def book(Dd):
    bk = (Dd / Dd.loc[:"2024"].std()).sum(axis=1); return bk * 0.15 / (bk.loc[:"2024"].std() * np.sqrt(365))


for nm, (fn, nb) in T.items():
    h = fn(); d = SB.daily(h); s = SB.periods(d)
    c1 = float(pd.concat([d, v], axis=1, sort=True).loc["2022":SB.END].corr().iloc[0, 1]); c2 = float(pd.concat([d, book0], axis=1, sort=True).loc["2020":SB.END].corr().iloc[0, 1])
    ok = bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c1) <= 0.2 and abs(c2) <= 0.5)
    r = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c1, 3), "corr book": round(c2, 3), "entry bar": ok}
    if ok:
        rb = [SB.periods(SB.daily(fn(x))) for x in nb] + [SB.periods(SB.daily(fn(lag=1)))]
        r["robustness (thr low / high / one day later)"] = rb; r["robust"] = bool(all(min(x) > 0 for x in rb))
        if r["robust"]:
            b0 = book(S.fillna(0.0)); b1 = book(pd.concat([S, d.rename(nm)], axis=1, sort=True).fillna(0.0))
            r["book 2020-24 without / with"] = [round(SB.sh(b0, "2020", "2024"), 3), round(SB.sh(b1, "2020", "2024"), 3)]
            if SB.sh(b1, "2020", "2024") > SB.sh(b0, "2020", "2024"):
                S = pd.concat([S, d.rename(nm)], axis=1, sort=True).fillna(0.0); r["added"] = True
    out[nm] = r; print(nm, r, flush=True)
bk = book(S.fillna(0.0)); out["BOOK"] = SB.evaluate(bk); out["BOOK"]["sleeves"] = list(S.columns)
vv = v.loc["2022":SB.END]; rho = float(pd.concat([vv, bk], axis=1, sort=True).loc["2022":SB.END].corr().iloc[0, 1]); sb = out["BOOK"]["EXPECTED LIVE (0.6 x 2020-26)"]
mix = lambda w: (1.78 + w * sb) / np.sqrt(1 + w * w + 2 * w * rho); bw = float(max(np.arange(0, 2.01, 0.05), key=mix))
out["mix with v8.6"] = {"best weight": round(bw, 2), "best": round(mix(bw), 3)}
print(json.dumps({"BOOK": out["BOOK"], "mix": out["mix with v8.6"]}, indent=0))
S.to_parquet(SB.ROOT / "results/gen364_sleeves.parquet"); bk.to_frame("stress book").to_parquet(SB.ROOT / "results/gen364_book.parquet")
json.dump(out, open(SB.ROOT / "results/gen364.json", "w"), indent=1)

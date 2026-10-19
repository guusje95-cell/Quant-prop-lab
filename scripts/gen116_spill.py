"""Gen116 (config/gen116_protocol.json): US equity session spillover into BTC/ETH and the Llorente volume-return rule.
Writes results/gen116.csv."""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}
exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], g)
CS, B, H6, B0, k0, per, sh, cst = (g[k] for k in ("CS", "B", "H6", "B0", "k0", "per", "sh", "cst"))
f = {"__file__": str(ROOT / "scripts/gen106_intraday.py")}
exec(open(ROOT / "scripts/gen106_intraday.py").read().split("\nb0, H0 = book(pos); k0")[0], f)
CB, IDXbf, book, sleeve, posbf = (f[k] for k in ("CB", "IDX", "book", "sleeve", "pos"))
bb0, HB0 = book(posbf); kb0 = per(bb0, "2022-01-01"); BB0 = sh(bb0, "2022-01-01", "2026-09-30")
END = "2026-09-30 23:00"; COINS = ["BTC", "ETH"]; rows = []
HC = CS._hourly_close(COINS).loc[:END]; RH = HC.pct_change(fill_method=None).fillna(0.0); FU = CS._funding_hourly(COINS, HC.index)


def perp(P):
    P = P.reindex(HC.index).fillna(0.0)
    return (P * RH).sum(axis=1) - (P * FU).sum(axis=1) - P.diff().abs().fillna(P.abs()).sum(axis=1) * 5 / 1e4


def evaluate(name, P):
    hp = perp(P); p = per(hp, "2020-01-01")
    v = CS.portfolio_v5(pd.concat([H6, hp.rename(name)], axis=1).fillna(0.0))[0]; k1 = per(v, "2022-01-01")
    hb = sleeve(P.reindex(columns=CB.CFD).fillna(0.0)); pb = per(hb, "2020-01-01")
    vb = CS.portfolio_v5(pd.concat([HB0, hb.rename(name)], axis=1).fillna(0.0))[0]; kb1 = per(vb, "2022-01-01")
    cor = lambda h: float(pd.concat([cst, h.groupby(h.index.floor("D")).sum()], axis=1).loc["2020":].corr().iloc[0, 1])
    r = {"test": name, "perp DEV/TEST/HOLD": np.round(p, 3).tolist(), "cfd DEV/TEST/HOLD": np.round(pb, 3).tolist(), "corr C*": round(cor(hp), 3),
         "v6 before/after": [round(B0, 3), round(sh(v, "2022-01-01", "2026-09-30"), 3)], "v6 TEST/HOLD before/after": [np.round(k0[1:], 3).tolist(), np.round(k1[1:], 3).tolist()],
         "bf before/after": [round(BB0, 3), round(sh(vb, "2022-01-01", "2026-09-30"), 3)], "bf TEST/HOLD before/after": [np.round(kb0[1:], 3).tolist(), np.round(kb1[1:], 3).tolist()]}
    r["pass v6"] = bool(p[0] > 0 and p[1] >= 0.8 and p[2] >= 0.5 and r["corr C*"] <= 0.3 and r["v6 before/after"][1] > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
    r["pass bf"] = bool(pb[0] > 0 and pb[1] >= 0.5 and pb[2] >= 0.3 and cor(hb) <= 0.3 and r["bf before/after"][1] > BB0 and kb1[1] >= kb0[1] and kb1[2] >= kb0[2])
    rows.append(r); print(r, flush=True)


ux = pd.read_parquet(ROOT / "research_data/dukascopy/US100_1h.parquet")["close"].astype("float64")
ux = ux[~ux.index.duplicated()].sort_index().loc["2019-12-01":END]
et = HC.index.tz_localize("UTC").tz_convert("America/New_York")
uet = ux.index.tz_localize("UTC").tz_convert("America/New_York")
U = pd.DataFrame({"c": ux.to_numpy(), "d": uet.date, "h": uet.hour}, index=ux.index)
c10 = U[U.h == 10].groupby("d").c.first(); c11 = U[U.h == 11].groupby("d").c.first(); c16 = U[U.h == 16].groupby("d").c.first()
o10 = U[U.h == 9].groupby("d").c.first()                      # close of the 09:00 bar = price at 10:00 ET
s1 = np.sign(c10 / o10 - 1).dropna()                           # 10:00-11:00 ET bar return: close of 10:00 bar vs close of 09:00 bar
s2 = np.sign(U[U.h == 15].groupby("d").c.first() / o10 - 1).dropna()   # 10:00 -> 16:00 ET (close of 15:00 bar)
d_et = pd.Series(et.date, index=HC.index); h_et = pd.Series(et.hour, index=HC.index)
P1 = pd.DataFrame(0.0, index=HC.index, columns=COINS); P2 = P1.copy()
m1 = h_et.between(11, 15); P1.loc[m1, :] = (0.5 * d_et[m1].map(s1).fillna(0.0)).to_numpy()[:, None]
m2 = h_et.between(16, 23); P2.loc[m2, :] = (0.5 * d_et[m2].map(s2).fillna(0.0)).to_numpy()[:, None]
evaluate("W1 US open spillover", P1)
evaluate("W2 US close spillover", P2)
W = pd.DataFrame(0.0, index=pd.date_range("2020-01-01", "2026-09-30"), columns=COINS)
for c in COINS:
    k = B.k5(c).loc[:END]; px = k.close.resample("1D").last(); vol = k.volume.resample("1D").sum()
    r = px.pct_change(); s = r.rolling(30).std().shift(1); lv = np.log(vol); v = (lv - lv.rolling(30).mean().shift(1)) / lv.rolling(30).std().shift(1)
    sig = np.where((r.abs() > s) & (v > 1), 0.5 * np.sign(r), np.where((r.abs() > s) & (v < 0), -0.5 * np.sign(r), 0.0))
    W[c] = pd.Series(sig, index=px.index).reindex(W.index).fillna(0.0)
evaluate("W3 Llorente volume-return", CB.d2h(W.reindex(columns=CB.CFD).fillna(0.0), HC.index)[COINS])
pd.DataFrame(rows).to_csv(ROOT / "results/gen116.csv", index=False)

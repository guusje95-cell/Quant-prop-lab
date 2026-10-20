"""Gen257 (config/gen257_protocol.json): betting-against-beta in bf2 + replication on the 40 extra coins. Writes results/gen257.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
END = L.END
g = {"__file__": str(L.ROOT / "scripts/gen196_bf_ridge.py")}; exec(open(L.ROOT / "scripts/gen196_bf_ridge.py").read().split("\nIS = (P6 + R1)")[0], g)
CS, HB0, per, sh, hb, P6, R1, CB, IDXbf, sleeve = (g[k] for k in ("CS", "HB0", "per", "sh", "hb", "P6", "R1", "CB", "IDXbf", "sleeve"))
q = {"__file__": str(L.ROOT / "scripts/gen232_bf_p1.py")}; exec(open(L.ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], q)
IS0 = (P6 + R1 + q["p1"]()).rename("vol-managed indices")
bk = lambda extra: CS.portfolio_v5(pd.concat([HB0, IS0, hb.rename("ridge ML")] + extra, axis=1).fillna(0.0))[0]
b0 = bk([]); B0, k0 = sh(b0, "2022-01-01", END), per(b0, "2022-01-01")


def bab(R, rb, n, min_n):
    beta = pd.DataFrame({c: R[c].rolling(90, min_periods=60).cov(rb) / rb.rolling(90, min_periods=60).var() for c in R.columns})
    rk = beta.rank(axis=1); cnt = beta.notna().sum(axis=1)
    lo = rk.le(n); hi = rk.gt(cnt - n, axis=0)
    sl, shh = 1 / beta.where(lo).mean(axis=1), 1 / beta.where(hi).mean(axis=1); m = pd.concat([sl, shh], axis=1).max(axis=1)
    w = lo.astype(float).mul(0.5 / n * sl / m, axis=0) - hi.astype(float).mul(0.5 / n * shh / m, axis=0)
    return w.mul((cnt >= min_n).astype(float), axis=0).fillna(0.0)


B = L.B; alts = [c for c in CB.CFD if c != "BTC"]
Pd = B.panel("close", "1D", ["BTC"] + alts).loc[:END]; Rd = Pd.pct_change(fill_method=None)
w = bab(Rd[alts], Rd["BTC"], 3, 8)
hc = sleeve(CB.d2h(w.reindex(columns=CB.CFD).fillna(0.0), IDXbf.append(pd.DatetimeIndex([IDXbf[-1] + pd.Timedelta(hours=1)]))))
s = per(hc, "2020-01-01"); b1 = bk([hc.rename("BAB")]); B1, k1 = sh(b1, "2022-01-01", END), per(b1, "2022-01-01")
out = {"reference bf2": [round(B0, 3), np.round(k0, 3).tolist()], "sleeve D/T/H": np.round(s, 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()]}
# replication on the 40 extra coins
X = L.ROOT / "research_data/binance_extra"; ex = sorted({p.name.split("USDT_")[0] for p in X.glob("*USDT_1h.parquet")})
hcx = pd.DataFrame({c: pd.read_parquet(X / f"{c}USDT_1h.parquet")["close"] for c in ex}); hcx.index = pd.DatetimeIndex(hcx.index)
hcx = hcx[~hcx.index.duplicated()].loc[:END + " 23:00"]
dcx = hcx.resample("1D").last(); Rx = dcx.pct_change(fill_method=None); rbx = Rd["BTC"].reindex(Rx.index)
wx = bab(Rx, rbx, 4, 10)
r = hcx.pct_change(fill_method=None).fillna(0.0)
held = wx.reindex(wx.index.append(pd.DatetimeIndex([wx.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
rep = (held * r).sum(axis=1) - held.diff().abs().sum(axis=1).where(r.index.hour == 0, 0.0) * 10 / 1e4
rd = rep.groupby(rep.index.floor("D")).sum(); S = lambda a, b: round(float(rd.loc[a:b].mean() / rd.loc[a:b].std() * np.sqrt(365)), 3)
out["replication 40 extra coins"] = {"2020-21": S("2020-06-01", "2021-12-31"), "2022": S("2022-01-01", "2022-12-31"), "2023-26": S("2023-01-01", END)}
out["pass"] = bool(s[0] > 0 and s[1] >= 0.5 and s[2] >= 0.3 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2]
                   and out["replication 40 extra coins"]["2022"] > 0 and out["replication 40 extra coins"]["2023-26"] > 0.5)
print(json.dumps(out)); json.dump(out, open(L.ROOT / "results/gen257.json", "w"), indent=1)

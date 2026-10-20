"""Gen255 (config/gen255_protocol.json): sign-reversed OI growth and top-trader change; replication on the 40 extra coins.
Writes results/gen255.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
B, END = L.B, L.END
out = {}; save = lambda: json.dump(out, open(L.ROOT / "results/gen255.json", "w"), indent=1)
C = B.coins(); P = B.panel("close", "1D", C).loc[:END]
met = {c: B.metrics(c) for c in C}
oi = pd.DataFrame({c: m["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1D").last() for c, m in met.items()}).reindex(P.index)
tt = pd.DataFrame({c: m["sum_toptrader_long_short_ratio"].pipe(lambda z: z.where(z > 0)).resample("1D").last() for c, m in met.items()}).reindex(P.index)
hA = L.perp(L.xs(np.log(oi / oi.shift(7)))); rA = L.judge("A reversed OI growth", hA, out)
# replication on the 40 extra coins
X = L.ROOT / "research_data/binance_extra"; ex = sorted({p.name.split("USDT_")[0] for p in X.glob("*USDT_1h.parquet")})
hc = pd.DataFrame({c: pd.read_parquet(X / f"{c}USDT_1h.parquet")["close"] for c in ex}).loc[:END + " 23:00"]
hc.index = pd.DatetimeIndex(hc.index); hc = hc[~hc.index.duplicated()]
oix = pd.DataFrame({c: pd.read_parquet(X / f"{c}USDT_oi_1h.parquet")["oi_value"] for c in ex}); oix.index = pd.DatetimeIndex(oix.index)
oid = oix.where(oix > 0).resample("1D").last()
w = L.xs(np.log(oid / oid.shift(7)), n=8, size=0.0625)
r = hc.pct_change(fill_method=None).fillna(0.0)
held = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
turn = held.diff().abs().sum(axis=1).where(r.index.hour == 0, 0.0)
rep = (held * r).sum(axis=1) - turn * 10 / 1e4
rd = rep.groupby(rep.index.floor("D")).sum()
S = lambda a, b: float(rd.loc[a:b].mean() / rd.loc[a:b].std() * np.sqrt(365))
out["A replication on 40 extra coins (8 per side)"] = {"2022": round(S("2022-01-01", "2022-12-31"), 3), "2023-26": round(S("2023-01-01", END), 3)}
out["A pass"] = bool(rA["pass"] and out["A replication on 40 extra coins (8 per side)"]["2022"] > 0 and out["A replication on 40 extra coins (8 per side)"]["2023-26"] > 0.5)
print(out["A replication on 40 extra coins (8 per side)"], flush=True); save()
hD = L.perp(L.xs(-np.log(tt / tt.shift(7)))); rD = L.judge("D reversed top-trader change", hD, out, dev_start=str(tt.dropna(how="all").index[0].date()))
d = hD.groupby(hD.index.floor("D")).sum(); yrs = {y: round(float(d.loc[str(y)].mean() / d.loc[str(y)].std() * np.sqrt(365)), 2) for y in range(2022, 2027)}
out["D by year"] = yrs; out["D pass"] = bool(rD["pass"] and sum(v > 0 for v in yrs.values()) >= 4); print(yrs, flush=True); save()

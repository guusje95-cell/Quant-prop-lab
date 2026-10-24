"""Gen360 (config/gen360_protocol.json): residual crash reversal, equity-stress buy, VIX-spike buy, market-wide capitulation.
Writes results/gen360.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
import futures_db as F
coins, idx, n, D, DR = SB.coins, SB.idx, SB.n, SB.D, SB.DR
book = pd.read_parquet(SB.ROOT / "results/gen359_book.parquet").iloc[:, 0]
S = {}
beta = DR.rolling(60, min_periods=50).cov(DR["BTC"]).div(DR["BTC"].rolling(60, min_periods=50).var(), axis=0).shift(1)
res = DR - beta.mul(DR["BTC"], axis=0); rsd = res.rolling(90, min_periods=60).std().shift(1)
mask = (res < -3 * rsd); mask["BTC"] = False
Pc = SB.daily_event_positions(mask, 1.0, 3)
bh = beta.reindex(D.index).shift(0).reindex(idx.floor("D")).set_axis(idx).ffill()
hedge = -(Pc.drop(columns=["BTC"]) * bh.drop(columns=["BTC"]).fillna(1.0)).sum(axis=1)
Pc["BTC"] = Pc["BTC"] + hedge
S["A residual crash reversal"] = SB.pnl(Pc, maker=True)
es = F.daily("ES")["r"]; es.index = pd.DatetimeIndex(es.index); z = es / es.rolling(250, min_periods=200).std().shift(1)
sig = pd.Series(0.0, index=D.index)
for d in z.index[z < -2.5]:
    sig.loc[d:d + pd.Timedelta(days=2)] = 1.0                                # row d (decided at d's crypto close) -> held d+1..d+3
w = pd.DataFrame({"BTC": 0.25 * sig, "ETH": 0.25 * sig}).reindex(columns=coins).fillna(0.0)
S["B equity-stress buy"] = SB.pnl(w.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0), maker=True)
vix = pd.read_parquet(SB.ROOT / "research_data/more2/vix_VIX.parquet")["close"]; vix.index = pd.DatetimeIndex(vix.index)
sig = pd.Series(0.0, index=D.index)
for d in vix.index[vix.pct_change() > 0.25]:
    sig.loc[d:d + pd.Timedelta(days=2)] = 1.0
w = pd.DataFrame({"BTC": 0.25 * sig, "ETH": 0.25 * sig}).reindex(columns=coins).fillna(0.0)
S["C VIX-spike buy"] = SB.pnl(w.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0), maker=True)
Z = SB.premium_z(); cnt = (Z < -3).sum(axis=1).to_numpy(); P = np.zeros((n, len(coins)))
for t in np.flatnonzero(cnt >= 8):
    for c in ("BTC", "ETH"):
        P[t + 1:min(t + 13, n), coins.index(c)] = 0.25
S["D market-wide capitulation"] = SB.pnl(pd.DataFrame(P, index=idx, columns=coins), maker=True)
out = {"events": {"B": int((z < -2.5).sum()), "C": int((vix.pct_change() > 0.25).sum()), "D hours": int((cnt >= 8).sum())}}
v = SB.v86_daily()
for nm, h in S.items():
    d = SB.daily(h); s = SB.periods(d)
    c1 = float(pd.concat([d, v], axis=1).loc["2022":SB.END].corr().iloc[0, 1]); c2 = float(pd.concat([d, book], axis=1).loc["2020":SB.END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c1, 3), "corr Gen359 book": round(c2, 3),
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c1) <= 0.2 and abs(c2) <= 0.5)}
    print(nm, out[nm], flush=True); d.to_frame(nm).to_parquet(SB.ROOT / f"results/gen360_{nm[0]}.parquet")
json.dump(out, open(SB.ROOT / "results/gen360.json", "w"), indent=1)

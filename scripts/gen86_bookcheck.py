"""Gen86 check: the book test with the Weiss-type 6-event live rule for event sleeves (P1 needs 30 nonzero days otherwise)."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/home/user/Quant-prop-lab"); sys.path.insert(0,str(ROOT/"scripts")); sys.path.insert(0,str(ROOT/"src"))
import crypto_sleeves as CS


def v5w(D, sleeves, weiss_scale=0.5):
    W = pd.DataFrame(np.nan, index=D.index, columns=list(sleeves))
    for m in D.index[~D.index.to_period("M").duplicated()]:
        hist = D.loc[m - pd.Timedelta(days=365):m - pd.Timedelta(days=1)]
        live = [c for c in sleeves if (hist[c] != 0).sum() >= (6 if (c == "Weiss expiry" or c.startswith("E")) else 30) and hist[c].std() > 0]
        if len(live) < 2: continue
        w = pd.Series(0.10 / (hist[live].std().to_numpy()), index=live) / len(live)
        if "Weiss expiry" in w: w["Weiss expiry"] *= weiss_scale
        W.loc[m, :] = 0.0; W.loc[m, w.index] = w.to_numpy()
    return W.ffill().fillna(0.0)
CS.v5_weights = v5w
C85=pd.read_parquet(ROOT/"results/cache_gen85_hourly.parquet"); E=pd.read_parquet(ROOT/"results/cache_gen86_hourly.parquet")
BASE={"C*":C85["B1 swap-aware C* thr 0.5"],"Weiss expiry":C85["ref Weiss BTC/ETH"]}
def sh(h):
    d=h.groupby(h.index.floor("D")).sum().loc["2022":"2026-09"]; return d.mean()/d.std()*np.sqrt(365)
idx=E.index
print("base",round(sh(CS.portfolio_v5(pd.DataFrame(BASE).reindex(idx).fillna(0))[0]),3))
for c in E: print(c, round(sh(CS.portfolio_v5(pd.DataFrame({**BASE,c:E[c]}).reindex(idx).fillna(0))[0]),3))

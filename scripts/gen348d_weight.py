"""Gen348d: weight of the premium-spike sleeve inside v8.6 (chosen on 2022-24), and separate-book mixes. Writes results/gen348d.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
END = L.END
h = pd.read_parquet(L.ROOT / "results/gen348_premium_spike.parquet")["premium spike"]
H = pd.concat([L.H6, L.RIDGE] + L.ALTK + [h], axis=1).fillna(0.0)
R = [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist(); out = {"reference v8.6": R}; res = {}
for m in (0.25, 0.5, 0.75):
    H2 = H.copy(); H2["premium spike"] = H2["premium spike"] * m          # the equal-risk weight is set on the scaled sleeve's own vol -> rescale after
    D = H.groupby(H.index.floor("D")).sum(); W = CS.v5_weights(D, list(H.columns)); W["premium spike"] *= m
    Wh = W.reindex(H.index.floor("D")).set_axis(H.index); raw = (H * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (0.15 / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1); x1 = rawd * lvl
    tgt = (0.15 / (x1.rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1); mult = (lvl * tgt).loc["2022-01-01":]
    b = (raw * mult.reindex(raw.index.floor("D")).set_axis(raw.index)).loc["2022-01-01":].dropna()
    k = [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()
    res[m] = {"D/T/H": k, "2022-24 Sharpe": round(L.sh(b, "2022-01-01", "2024-12-31"), 3)}; print(m, res[m], flush=True)
out["by multiplier"] = res
best = max(res, key=lambda m: res[m]["2022-24 Sharpe"]); k = res[best]["D/T/H"]
out["chosen on 2022-24"] = best
out["v8.7 candidate"] = bool(k[3] >= R[3] and k[0] >= R[0] + 0.05 and all(a >= q for a, q in zip(k[1:], R[1:])))
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); sd = h.groupby(h.index.floor("D")).sum().loc["2022":END]
V = vd / vd.loc["2022":"2024"].std(); S = sd / sd.loc["2022":"2024"].std()
f = lambda x, a, z: round(float(x.loc[a:z].mean() / x.loc[a:z].std() * np.sqrt(365)), 3)
for wgt in (0.25, 0.5, 1.0):
    mx = V + wgt * S; out[f"separate books, v8.6 + {wgt} x spike (equal-risk units)"] = [f(mx, "2022", END), f(mx, "2022", "2022"), f(mx, "2023", "2024"), f(mx, "2025", END)]
out["corr daily 2022-26"] = round(float(pd.concat([vd, sd], axis=1).loc["2022":END].corr().iloc[0, 1]), 3)
print(json.dumps(out, indent=0)); json.dump(out, open(L.ROOT / "results/gen348d.json", "w"), indent=1)

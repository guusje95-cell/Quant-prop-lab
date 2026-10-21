"""Gen265 (config/gen265_protocol.json): Google-attention momentum (BTC/ETH) and attention-spike de-risking of the book (vs v8.1).
Writes results/gen265.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
END = L.END; days = pd.date_range("2020-01-01", END)
g = pd.read_parquet(L.ROOT / "research_data/attention/google_bitcoin_1d.parquet")["interest"]; g.index = pd.DatetimeIndex(g.index).normalize()
a = np.log(g.clip(lower=0.1)).reindex(days).ffill()
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
for lag, tag in ((1, ""), (2, " [descriptive: values used 2 days later]")):
    ax = a.shift(lag)                                                 # row d (decided at d's close, held d+1) uses values to d - lag
    s = ax.rolling(7).mean() - ax.rolling(30).mean(); z = (s - s.rolling(90, min_periods=60).mean()) / s.rolling(90, min_periods=60).std()
    w = pd.Series(np.where(z > 1, 0.25, np.where(z < -1, -0.25, 0.0)), index=days)
    r = L.judge("A attention momentum" + tag, L.perp(pd.DataFrame({"BTC": w, "ETH": w})), out)
    if lag == 2:
        r["pass"] = None
# B: de-risk the whole v8.1 book the day after an attention spike
b0 = L.V7; d0 = L.sh(b0, "2022-01-01", END)
for lag, tag in ((1, ""), (2, " [descriptive: 2-day delay]")):
    x = a.shift(lag); zz = (x - x.shift(1).rolling(30).mean()) / x.shift(1).rolling(30).std()   # spike of day t-lag vs the 30 days before
    mult = pd.Series(np.where(zz > 2, 0.5, 1.0), index=days)
    b1 = b0 * mult.reindex(b0.index.floor("D")).fillna(1.0).to_numpy()
    B1, k1 = L.sh(b1, "2022-01-01", END), L.per(b1, "2022-01-01")
    out["B attention-spike de-risk" + tag] = {"spike days": int((mult < 1).sum()), "book": [round(B1, 3), np.round(k1, 3).tolist()],
        "pass": (bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2]) if lag == 1 else None)}
    print(out["B attention-spike de-risk" + tag], flush=True)
json.dump(out, open(L.ROOT / "results/gen265.json", "w"), indent=1)

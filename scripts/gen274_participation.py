"""Gen274 (config/gen274_protocol.json): average trade size XS; altcoin OI share rotation (vs v8.1). Writes results/gen274.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
B, END = L.B, L.END; days = pd.date_range("2020-01-01", END); C = B.coins()
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}; save = lambda: json.dump(out, open(L.ROOT / "results/gen274.json", "w"), indent=1)
QV = B.panel("quote_volume", "1D", C).reindex(days); N = B.panel("count", "1D", C).reindex(days).replace(0, np.nan)
ats = (QV / N).replace(0, np.nan)
L.judge("A average trade size XS", L.perp(L.xs(np.log(ats.rolling(7, min_periods=5).mean() / ats.rolling(90, min_periods=60).mean()))), out); save()
oi = pd.DataFrame({c: B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1D").last() for c in C}).reindex(days)
alts = [c for c in C if c not in ("BTC", "ETH")]
share = oi[alts].sum(axis=1, min_count=10) / oi.sum(axis=1, min_count=12)
s = share - share.shift(7); z = (s - s.rolling(90, min_periods=60).mean()) / s.rolling(90, min_periods=60).std()
sg = pd.Series(np.where(z > 1, 1.0, np.where(z < -1, -1.0, 0.0)), index=days)
W = pd.DataFrame(0.0, index=days, columns=C); W["BTC"] = 0.5 * sg
for c in alts:
    W[c] = -0.5 / len(alts) * sg
L.judge("B altcoin OI share rotation", L.perp(W), out); save()

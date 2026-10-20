"""Gen258 (config/gen258_protocol.json): ridge + market breadth features; recency-weighted ridge. Writes results/gen258.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import v7lab as L
import bf2lab as F
import ridge_live as RL
B, END = L.B, L.END
out = {"reference v7": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
save = lambda: json.dump(out, open(L.ROOT / "results/gen258.json", "w"), indent=1)
D0 = RL.features(END); days = pd.DatetimeIndex(sorted(D0["day"].unique()))
C = B.coins(); P = B.panel("close", "1D", C).reindex(days); R = P.pct_change(fill_method=None)
fu = B.funding_panel(C); fu.index = (fu.index - pd.Timedelta(seconds=1)).floor("D"); FD = fu.groupby(level=0).sum().reindex(days)
oi = pd.DataFrame({c: B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1D").last() for c in C}).reindex(days)
tot = oi.sum(axis=1, min_count=10)
mkt = pd.DataFrame({"breadth": (P > P.rolling(30).mean()).where(P.notna()).mean(axis=1), "fund_avg": FD.mean(axis=1),
                    "oi_agg": tot / tot.shift(7) - 1, "disp": R.std(axis=1)}, index=days)


def walk(D, feats, half_life=None):
    pred = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["target"])
        te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        sw = None if half_life is None else 0.5 ** ((m - tr["day"]).dt.days.to_numpy() / half_life)
        mdl = Ridge(alpha=10.0).fit(Xtr, tr["target"], sample_weight=sw); s = np.std(mdl.predict(Xtr)) or 1.0
        pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    return D.assign(p=pred).pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5


base = [x for x in D0.columns if x not in ("day", "target", "coin")]
DA = D0.join(mkt, on="day")
wA = walk(DA, base + list(mkt.columns))
L.judge("A ridge + market breadth", L.perp(wA), out, dev_start="2021-01-01", replace_ridge=True); F.judge("A ridge + market breadth", F.cfd(wA), out, dev_start="2021-01-01", replace_ridge=True); save()
wB = walk(D0, base, half_life=365)
L.judge("B recency-weighted ridge", L.perp(wB), out, dev_start="2021-01-01", replace_ridge=True); F.judge("B recency-weighted ridge", F.cfd(wB), out, dev_start="2021-01-01", replace_ridge=True); save()

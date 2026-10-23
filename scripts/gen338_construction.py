"""Gen338 (config/gen338_protocol.json): EWMA / blended vol targeting and equal-risk-contribution sleeve weights for v8.6.
Writes results/gen338.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
END = L.END
H = pd.concat([L.H6, L.RIDGE] + L.ALTK, axis=1).fillna(0.0)
D = H.groupby(H.index.floor("D")).sum()


def erc_weights(D, sleeves, shrink=0.5, weiss_scale=0.5):
    W = pd.DataFrame(np.nan, index=D.index, columns=list(sleeves))
    for m in D.index[~D.index.to_period("M").duplicated()]:
        hist = D.loc[m - pd.Timedelta(days=365):m - pd.Timedelta(days=1)]
        live = [c for c in sleeves if (hist[c] != 0).sum() >= (6 if c == "Weiss expiry" else 30) and hist[c].std() > 0]
        if len(live) < 2:
            continue
        S = hist[live].cov().to_numpy() * 365; S = (1 - shrink) * S + shrink * np.diag(np.diag(S))
        b = np.ones(len(live)); b[[i for i, c in enumerate(live) if c == "Weiss expiry"]] = weiss_scale; b = b / b.sum()
        x = b / np.sqrt(np.diag(S))
        for _ in range(500):                                      # risk-budget fixed point: risk contribution of i -> b_i
            rc = x * (S @ x) / (x @ S @ x); x = x * np.sqrt(b / np.maximum(rc, 1e-12)); x = x / x.sum()
        vol = np.sqrt(x @ S @ x); x = x * 0.10 / vol / len(live) * np.sqrt(len(live))   # scale; the level multiplier sets the final vol anyway
        W.loc[m, :] = 0.0; W.loc[m, live] = x
    return W.ffill().fillna(0.0)


def portfolio(W, volmode="30d", vol=0.15, start="2022-01-01"):
    Wh = W.reindex(H.index.floor("D")).set_axis(H.index)
    raw = (H * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (vol / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1); x1 = rawd * lvl
    if volmode == "30d":
        sd = x1.rolling(30).std()
    elif volmode == "ewma":
        sd = np.sqrt((x1 ** 2).ewm(halflife=10, min_periods=30).mean())
    else:
        sd = (x1.rolling(30).std() + x1.rolling(90, min_periods=30).std()) / 2
    tgt = (vol / (sd * np.sqrt(365))).clip(upper=1.5).shift(1)
    mult = (lvl * tgt).loc[start:]
    return (raw * mult.reindex(raw.index.floor("D")).set_axis(raw.index)).loc[start:].dropna()


W0 = CS.v5_weights(D, list(H.columns))
ref = portfolio(W0); assert abs(L.sh(ref, "2022-01-01", END) - L.REF[0]) < 1e-9
R = [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist(); out = {"reference v8.6": R}
for nm, p in (("A EWMA vol target", portfolio(W0, "ewma")), ("B blended 30/90-day vol target", portfolio(W0, "blend")),
              ("C equal risk contribution", portfolio(erc_weights(D, list(H.columns))))):
    k = [round(L.sh(p, "2022-01-01", END), 3)] + np.round(L.per(p, "2022-01-01"), 3).tolist()
    out[nm] = {"v8.6 D/T/H": k, "strict pass": bool(all(a >= c for a, c in zip(k[1:], R[1:])) and k[0] >= R[0] + 0.05)}
    print(nm, out[nm], flush=True)
json.dump(out, open(L.ROOT / "results/gen338.json", "w"), indent=1)

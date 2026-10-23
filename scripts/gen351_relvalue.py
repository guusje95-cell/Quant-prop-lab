"""Gen351 (config/gen351_protocol.json): distance pairs, weekday seasonality XS, long-term reversal XS. Writes results/gen351.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
END = L.END; ROOT = L.ROOT
coins = CS._breadth_universe(); H = CS._breadth_close(coins); P = H.resample("1D").last().loc[:END]
listed = P.notna().cumsum() >= 60; dr = P.pct_change(fill_method=None); vol = dr.rolling(30).std(); days = P.index


def xs_w(score, hold=None):
    rk = score.where(listed).rank(axis=1, pct=True); iv = (1 / vol).where(listed)
    wl, ws = iv.where(rk > 2 / 3, 0.0), iv.where(rk <= 1 / 3, 0.0)
    w = (wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)).fillna(0.0)
    return CS._hold(w, hold, True) if hold else w


# A distance pairs: W row d = held during d+1 (decided at d's close)
W = pd.DataFrame(0.0, index=days, columns=coins); lp = np.log(P)
for m in days[~days.to_period("M").duplicated()]:
    if m < pd.Timestamp("2019-12-01"):
        continue
    form = P.loc[m - pd.Timedelta(days=120):m - pd.Timedelta(days=1)]
    ok = [c for c in coins if form[c].notna().all() and len(form) >= 110]
    if len(ok) < 6:
        continue
    N = form[ok] / form[ok].iloc[0]; A = N.to_numpy()
    ssd = ((A[:, :, None] - A[:, None, :]) ** 2).sum(axis=0); iu = np.triu_indices(len(ok), 1)
    order = np.argsort(ssd[iu]); used = {}; pairs = []
    for k in order:
        i, j = iu[0][k], iu[1][k]
        if used.get(i, 0) < 2 and used.get(j, 0) < 2:
            pairs.append((ok[i], ok[j])); used[i] = used.get(i, 0) + 1; used[j] = used.get(j, 0) + 1
        if len(pairs) == 10:
            break
    mend = (m + pd.offsets.MonthEnd(0)).normalize(); mdays = days[(days >= m) & (days <= mend)]
    for a, b in pairs:
        f = lp[a].loc[form.index] - lp[b].loc[form.index]; mu, sd = f.mean(), f.std(); s = (lp[a] - lp[b] - mu) / sd
        state, age = 0, 0
        for d in mdays:
            z = s.get(d, np.nan)
            if not np.isfinite(z):
                continue
            if state == 0 and abs(z) > 2:
                state, age = -np.sign(z), 0
            elif state != 0 and (np.sign(z) == state or age >= 20 or d == mend):
                state = 0
            if state != 0:
                W.loc[d, a] += 0.1 * state; W.loc[d, b] -= 0.1 * state; age += 1
S = {"A distance pairs": CS.premium_carry_breadth(coins=coins, w=W)}
wd = pd.DataFrame(np.nan, index=days, columns=coins)
for k in range(7):
    m = days.weekday == k; x = dr[m].rolling(8, min_periods=6).mean()           # same-weekday mean over the last 8 such days (incl. today's weekday)
    wd.loc[m] = x.to_numpy()
score_B = wd.shift(6)                                                         # row d (decided at d's close, held d+1): weekday of d+1 = weekday of d-6
S["B weekday seasonality XS"] = CS.premium_carry_breadth(coins=coins, w=xs_w(score_B))
S["C long-term reversal XS"] = CS.premium_carry_breadth(coins=coins, w=xs_w(-(P.shift(30) / P.shift(180) - 1), 7))
spike = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet")["premium spike"]
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); sd_ = spike.groupby(spike.index.floor("D")).sum(); out = {}
for nm, h in S.items():
    h = h.loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0); s = [round(x, 3) for x in L.per(h, "2020-01-01")]; d = h.groupby(h.index.floor("D")).sum()
    c = float(pd.concat([d, vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1]); c2 = float(pd.concat([d, sd_], axis=1).loc["2020":END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "corr premium spike": round(c2, 3),
               "pass": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2 and abs(c2) <= 0.5)}
    print(nm, out[nm], flush=True); h.to_frame(nm).to_parquet(ROOT / f"results/gen351_{nm[0]}.parquet")
json.dump(out, open(ROOT / "results/gen351.json", "w"), indent=1)

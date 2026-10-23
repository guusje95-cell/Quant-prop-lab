"""Gen358 (config/gen358_protocol.json): stress-reversion book. Writes results/gen358.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
END = L.END; ROOT = L.ROOT
sp = pd.read_parquet(ROOT / "results/gen348_premium_spike.parquet").iloc[:, 0]
cr = pd.read_parquet(ROOT / "results/gen357_crashrev.parquet").iloc[:, 0]
nf = pd.read_parquet(ROOT / "results/gen355_negfunding.parquet").iloc[:, 0]
dd = lambda s: s.groupby(s.index.floor("D")).sum().loc["2020-01-01":END]
D = pd.concat([dd(sp).rename("premium spike"), dd(cr).rename("crash reversal"), dd(nf).rename("negative funding")], axis=1).fillna(0.0)
vd = dd(L.V7)
f = lambda x, a, z: round(float(x.loc[a:z].mean() / x.loc[a:z].std() * np.sqrt(365)), 3)
per3 = lambda x: [f(x, "2020", "2022"), f(x, "2023", "2024"), f(x, "2025", END)]
out = {"sleeve corr": D.corr().round(3).to_dict()}
H = pd.concat([L.H6, L.RIDGE] + L.ALTK, axis=1).fillna(0.0); R0 = [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist()
for nm, cols in (("Book A (2 candidates)", ["premium spike", "crash reversal"]), ("Book B (+ negative funding)", ["premium spike", "crash reversal", "negative funding"])):
    sd = D[cols].loc[:"2024"].std(); bk = (D[cols] / sd).sum(axis=1); bk = bk * 0.15 / (bk.loc[:"2024"].std() * np.sqrt(365))
    eq = (1 + bk).cumprod(); r = {"Sharpe 2020-22 / 2023-24 / 2025-26": per3(bk), "by year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in bk.groupby(bk.index.year)},
                                  "max drawdown at 15% vol": round(float((eq / eq.cummax() - 1).min()), 3),
                                  "corr v8.6 2022-26": round(float(pd.concat([bk, vd], axis=1).loc["2022":END].corr().iloc[0, 1]), 3)}
    V = vd / vd.loc["2022":"2024"].std(); Bz = bk.loc["2022":] / bk.loc["2022":"2024"].std()
    for w in (1.0, 0.5):
        mx = (V + w * Bz).dropna(); r[f"separate accounts v8.6 + {w} x book (backtest) 2022-26 / 2022 / TEST / HOLD"] = [f(mx, "2022", END), f(mx, "2022", "2022"), f(mx, "2023", "2024"), f(mx, "2025", END)]
    Vp = V - (V.loc["2022":END].mean() - 1.78 * V.loc["2022":END].std() / np.sqrt(365))
    bs = f(Bz, "2022", END); Bp = Bz - (Bz.loc["2022":END].mean() - 0.6 * bs * Bz.loc["2022":END].std() / np.sqrt(365))
    r["planning: v8.6 alone / + 0.5 x book / + 1.0 x book"] = [f(Vp, "2022", END), f((Vp + 0.5 * Bp).dropna(), "2022", END), f((Vp + Bp).dropna(), "2022", END)]
    hb = sum((pd.read_parquet(ROOT / p).iloc[:, 0] / sd[c] / 24) for c, p in (("premium spike", "results/gen348_premium_spike.parquet"), ("crash reversal", "results/gen357_crashrev.parquet"),
                                                                         ("negative funding", "results/gen355_negfunding.parquet")) if c in cols)
    hb = hb.reindex(L.H6.index).fillna(0.0).rename("stress book"); res = {}
    for m in (0.25, 0.5, 1.0):
        Dh = pd.concat([H, hb], axis=1).fillna(0.0); Dd = Dh.groupby(Dh.index.floor("D")).sum(); W = CS.v5_weights(Dd, list(Dh.columns)); W["stress book"] *= m
        Wh = W.reindex(Dh.index.floor("D")).set_axis(Dh.index); raw = (Dh * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
        lvl = (0.15 / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1); x1 = rawd * lvl
        tgt = (0.15 / (x1.rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1); mult = (lvl * tgt).loc["2022-01-01":]
        b = (raw * mult.reindex(raw.index.floor("D")).set_axis(raw.index)).loc["2022-01-01":].dropna()
        res[m] = {"D/T/H": [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist(), "2022-24": round(L.sh(b, "2022-01-01", "2024-12-31"), 3)}
    best = max(res, key=lambda m: res[m]["2022-24"]); k = res[best]["D/T/H"]
    r["inside v8.6"] = {"by multiplier": res, "chosen on 2022-24": best,
                        "strict pass": bool(all(a >= q for a, q in zip(k[1:], R0[1:])) and k[0] >= R0[0] + 0.05)}
    out[nm] = r; print(nm, json.dumps(r), flush=True)
    bk.to_frame(nm).to_parquet(ROOT / f"results/gen358_{nm[5]}.parquet")
json.dump(out, open(ROOT / "results/gen358.json", "w"), indent=1)

"""v9.9 R24 (research/v99/r24_26_protocol.json): walk-forward meta-labeling of trend-4h trades. Writes results/v99/r24_meta_trend.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B
COINS = ("BTC", "ETH", "SOL")


def trades(idx):
    btc = B.k5("BTC").close.resample("1D").last(); b30 = np.log(btc / btc.shift(30))
    out = []
    for coin in COINS:
        pnl, P = CS.trend4h(coins=(coin,), positions=True)
        k = B.k5(coin); c4 = k.close.resample("4h").last(); h4 = k.high.resample("4h").max().loc[c4.index]; l4 = k.low.resample("4h").min().loc[c4.index]
        tr = pd.concat([h4 - l4, (h4 - c4.shift()).abs(), (l4 - c4.shift()).abs()], axis=1).max(axis=1).rolling(20).mean()
        hi, lo = h4.rolling(20).max().shift(1), l4.rolling(20).min().shift(1); vol = c4.pct_change().rolling(180).std() * np.sqrt(6 * 365)
        f = B.funding(coin)
        held = P[coin].reindex(idx).fillna(0.0); pnl = pnl.reindex(idx).fillna(0.0) / len(COINS)
        sgn = np.sign(held).to_numpy(); chg = np.r_[True, sgn[1:] != sgn[:-1]]
        starts = np.where(chg & (sgn != 0))[0]
        for a in starts:
            z = a
            while z + 1 < len(sgn) and sgn[z + 1] == sgn[a]:
                z += 1
            t0 = idx[a]; side = sgn[a]; bar = t0 - pd.Timedelta(hours=4)               # the 4-hour bar whose close triggered the entry
            if bar not in c4.index or not np.isfinite(tr.get(bar, np.nan)):
                continue
            strength = (c4[bar] - (hi[bar] if side > 0 else lo[bar])) * side / tr[bar]
            d = t0.floor("D") - pd.Timedelta(days=1); fr = f.loc[:t0 - pd.Timedelta(hours=1)]
            out.append({"entry": t0, "exit": idx[min(z + 1, len(idx) - 1)], "seg": pnl.iloc[a:z + 1], "pnl": float(pnl.iloc[a:z + 1].sum()),
                        "x": [float(strength), float(side * b30.get(d, np.nan)), float(vol.get(bar, np.nan)), float(side * (fr.iloc[-1] if len(fr) else 0.0)), float(side)]})
    return sorted(out, key=lambda t: t["entry"])


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    ref = book(V8); T = trades(idx)
    X = np.nan_to_num(np.array([t["x"] for t in T])); y = np.array([t["pnl"] > 0 for t in T]); ex = np.array([t["exit"] for t in T])
    mA, mB, Pp = np.ones(len(T)), np.ones(len(T)), np.full(len(T), np.nan)
    for i, t in enumerate(T):
        tr = np.where(ex < t["entry"])[0]
        if len(tr) < 60 or len(set(y[tr])) < 2:
            continue
        sc = StandardScaler().fit(X[tr]); m = LogisticRegression(C=1.0).fit(sc.transform(X[tr]), y[tr])
        p = m.predict_proba(sc.transform(X[i:i + 1]))[0, 1]; Pp[i] = p
        mA[i] = 1.0 if p >= 0.5 else 0.0; mB[i] = float(np.clip(p / m.predict_proba(sc.transform(X[tr]))[:, 1].mean(), 0.5, 1.5))
    pn = np.array([t["pnl"] for t in T]); s = ~np.isnan(Pp)
    out = {"reference v9.8": ref, "trades": len(T), "scored": int(s.sum()), "win rate": round(float(y.mean()), 3),
           "scored mean P&L bp p>=0.5 / p<0.5": [round(float(pn[s & (Pp >= 0.5)].mean() * 1e4), 2), round(float(pn[s & (Pp < 0.5)].mean() * 1e4), 2)]}
    for name, mu in (("A filter", mA), ("B sizer", mB)):
        delta = sum(((m_ - 1) * t["seg"].reindex(idx).fillna(0.0) for m_, t in zip(mu, T) if m_ != 1), pd.Series(0.0, index=idx))
        r = book(V8.assign(**{"trend 4h": V8["trend 4h"] + delta})); out[name] = {"book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r24_meta_trend.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

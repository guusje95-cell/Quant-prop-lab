"""v9.9 R23 (research/v99/r23_protocol.json): walk-forward meta-labeling of the v9.8 event-short trades. Writes results/v99/r23_meta_event.json."""
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


def trades(idx):
    s, pos, ev = EL.pnl(idx); CF = {sym[:-4]: (c, f) for sym, t0, c, f in ev}
    btc = B.k5("BTC").close.resample("1D").last(); br = np.log(btc).diff()
    b_ret = np.log(btc / btc.shift(30)); b_vol = br.rolling(30).std()
    out = []
    for n in pos.columns:
        p = pos[n]
        if not (p != 0).any():
            continue
        if n.startswith("spo_"):
            c, f = EL._closes(n[4:])
        else:
            c, f = CF.get(n, (None, None))
            if c is None:
                c, f = EL._closes(n)
        if c is None:
            continue
        c = c[~c.index.duplicated()]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = pd.Series(dtype=float) if f is None or not len(f) else f.copy()
        if len(fu):
            fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum()
        fu = fu.reindex(idx).fillna(0.0) if len(fu) else pd.Series(0.0, index=idx)
        h = p * r - p * fu - p.diff().abs().fillna(p.abs()) * 1e-3
        nz = (p != 0).to_numpy(); starts = np.where(nz & ~np.r_[False, nz[:-1]])[0]; ends = np.where(nz & ~np.r_[nz[1:], False])[0]
        for a, z in zip(starts, ends):
            t0 = idx[a]; tz = idx[min(z + 1, len(idx) - 1)]; seg = h.iloc[a:z + 2]
            past = c.loc[:t0 - pd.Timedelta(hours=1)]
            if len(past) < 2:
                continue
            ru = np.log(past.iloc[-1] / past.loc[t0 - pd.Timedelta(hours=25):].iloc[0])
            fr = f.loc[:t0 - pd.Timedelta(hours=1)].iloc[-1] if f is not None and len(f.loc[:t0 - pd.Timedelta(hours=1)]) else 0.0
            d = t0.floor("D") - pd.Timedelta(days=1)
            out.append({"col": n, "entry": t0, "exit": tz, "pnl": float(seg.sum()), "seg": seg,
                        "x": [float(ru), float(fr), float(b_ret.get(d, np.nan)), float(b_vol.get(d, np.nan)), float(n.startswith("spo_"))]})
    return s, out


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda s: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(V7.assign(**{"listing short": s}))[0]))
    s8, T = trades(idx); T.sort(key=lambda t: t["entry"]); ref = book(s8)
    rebuilt = sum((t["seg"].reindex(idx).fillna(0.0) for t in T), pd.Series(0.0, index=idx))
    X = np.nan_to_num(np.array([t["x"] for t in T])); y = np.array([t["pnl"] > 0 for t in T]); exits = np.array([t["exit"] for t in T])
    mA, mB, P = np.ones(len(T)), np.ones(len(T)), np.full(len(T), np.nan)
    for i, t in enumerate(T):
        tr = np.where(exits < t["entry"])[0]
        if len(tr) < 60 or len(set(y[tr])) < 2:
            continue
        sc = StandardScaler().fit(X[tr]); m = LogisticRegression(C=1.0).fit(sc.transform(X[tr]), y[tr])
        p = m.predict_proba(sc.transform(X[i:i + 1]))[0, 1]; pin = m.predict_proba(sc.transform(X[tr]))[:, 1].mean(); P[i] = p
        mA[i] = 1.0 if p >= 0.5 else 0.0; mB[i] = float(np.clip(p / pin, 0.5, 1.5))
    def cand(mult):
        return s8 + sum(((mu - 1) * t["seg"].reindex(idx).fillna(0.0) for mu, t in zip(mult, T) if mu != 1), pd.Series(0.0, index=idx))
    pn = np.array([t["pnl"] for t in T]); sc_ = ~np.isnan(P)
    out = {"reference v9.8": ref, "trades": len(T), "scored walk-forward": int(sc_.sum()), "win rate": round(float(y.mean()), 3),
           "corr(rebuilt trade sum, real sleeve) daily": round(float(dd(rebuilt).corr(dd(s8))), 3),
           "scored trades: mean P&L (bp of equity) p>=0.5 / p<0.5": [round(float(pn[sc_ & (P >= 0.5)].mean() * 1e4), 2) if (sc_ & (P >= 0.5)).any() else None,
                                                                   round(float(pn[sc_ & (P < 0.5)].mean() * 1e4), 2) if (sc_ & (P < 0.5)).any() else None],
           "share skipped by A": round(float((mA == 0).mean()), 3)}
    for name, mu in (("A filter", mA), ("B sizer", mB)):
        r = book(cand(mu)); out[name] = {"book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r23_meta_event.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

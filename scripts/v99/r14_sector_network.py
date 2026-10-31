"""v9.9 R14 (research/v99/r14_protocol.json): sector momentum and network momentum, cross-sectional, 60 perps.
Writes results/v99/r14_sector_network.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B, extra_pack as X
P = json.loads((ROOT / "research/v99/r14_protocol.json").read_text()); SECT = P["sectors"]; COST = 8e-4
COINS = [c for s in SECT.values() for c in s]


def load():
    C, F = {}, {}
    for c in COINS:
        if c in B.coins():
            s = B.k5(c)["close"].resample("1h").last(); f = B.funding(c)
        else:
            s = X.close_1h(c); f = X.funding(c)
        s.index = pd.DatetimeIndex(s.index).as_unit("ns") + pd.Timedelta(hours=1)          # stamp = time the close is known
        f.index = pd.DatetimeIndex(f.index).as_unit("ns")
        C[c] = s[~s.index.duplicated()]; F[c] = f[~f.index.duplicated()]
    C = pd.DataFrame(C).sort_index().loc["2021-01-01":"2026-10-01"]; F = pd.DataFrame(F).reindex(C.index).fillna(0.0)
    return C, F


def weights(C, kind):
    D = C.resample("1D", label="right", closed="right").last()                               # daily closes known at 00:00
    R = D.pct_change(fill_method=None); elig = D.notna().rolling(120).sum() >= 120
    mondays = [t for t in D.index if t.dayofweek == 0 and t >= pd.Timestamp("2021-12-27")]
    W = {}
    for t in mondays:
        e = [c for c in D.columns if elig.loc[t, c] and np.isfinite(D.loc[t, c])]
        if len(e) < 15:
            continue
        m30 = D.loc[t, e] / D[e].shift(30).loc[t] - 1; vol = R[e].loc[:t].tail(90).std() * np.sqrt(365)
        w = pd.Series(0.0, index=D.columns)
        if kind == "A":
            sr = {s: m30[[c for c in cs if c in e]].mean() for s, cs in SECT.items() if sum(c in e for c in cs) >= 2}
            rank = sorted(sr, key=sr.get)
            for s, sg in [(x, -1) for x in rank[:2]] + [(x, 1) for x in rank[-2:]]:
                cs = [c for c in SECT[s] if c in e]; w[cs] += sg * 0.25 / len(cs)
        else:
            m = (m30 / vol).replace([np.inf, -np.inf], np.nan).dropna(); e = list(m.index)
            corr = R[e].loc[:t].tail(90).corr()
            s = pd.Series({c: m[corr[c].drop(c).nlargest(5).index].mean() for c in e})
            if kind == "C":
                s = s - m
            q = max(len(s) // 5, 1); r = s.sort_values()
            w[r.index[:q]] -= 0.5 / q; w[r.index[-q:]] += 0.5 / q
        W[t] = w
    return pd.DataFrame(W).T


def sleeve(C, F, W):
    ret = C.pct_change(fill_method=None).fillna(0.0)
    pos = W.reindex(ret.index, method="ffill").fillna(0.0)                                   # set at Monday 00:00, earns from the next hour
    pos = pos.where(C.notna(), 0.0)
    pnl = (pos.shift(1) * ret).sum(axis=1) - (pos.shift(1) * F).sum(axis=1) - pos.diff().abs().sum(axis=1) * COST
    return pnl


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    b0 = unit(CS.portfolio_v5(V8)[0]); ref = [shp(b0, "2022", "2026-09-30"), per(b0)]
    C, F = load(); out = {"reference v9.8": ref, "coins loaded": int(C.notna().any().sum())}
    for k, name in (("A", "A sector momentum"), ("B", "B network momentum"), ("C", "C network minus own")):
        W = weights(C, k); h = sleeve(C, F, W).reindex(idx).fillna(0.0)
        b = unit(CS.portfolio_v5(V8.assign(**{name: h}))[0]); r = [shp(b, "2022", "2026-09-30"), per(b)]
        out[name] = {"rebalances": len(W), "gross exposure": round(float(W.abs().sum(axis=1).mean()), 2), "sleeve 2022 / 23-24 / 25-26": per(h),
                     "corr with v9.8 (daily)": round(float(dd(h.loc["2022":]).corr(dd(b0))), 3), "book": r,
                     "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    (ROOT / "results/v99/r14_sector_network.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

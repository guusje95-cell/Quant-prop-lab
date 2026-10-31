"""v9.9 R15 (research/v99/r15_protocol.json): co-skewness and downside-beta cross-sectional sleeves vs BTC on 59 perps.
Writes results/v99/r15_coskew.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import r14_sector_network as R14


def weights(C, kind):
    D = C.resample("1D", label="right", closed="right").last(); R = D.pct_change(fill_method=None)
    elig = D.notna().rolling(120).sum() >= 120; W = {}
    for t in [t for t in D.index if t.dayofweek == 0 and t >= pd.Timestamp("2021-12-27")]:
        e = [c for c in D.columns if c != "BTC" and elig.loc[t, c] and np.isfinite(D.loc[t, c])]
        if len(e) < 15:
            continue
        w = pd.Series(0.0, index=D.columns)
        if kind == "A":
            x = R[e + ["BTC"]].loc[:t].tail(90).dropna(axis=1, thresh=80).fillna(0.0)
            m = x["BTC"] - x["BTC"].mean(); ei = x.drop(columns="BTC"); ei = ei - ei.mean()
            s = (ei.mul(m ** 2, axis=0)).mean() / (np.sqrt((ei ** 2).mean()) * (m ** 2).mean())
            r = s.sort_values(); q = max(len(r) // 5, 1)
            w[r.index[:q]] += 0.5 / q; w[r.index[-q:]] -= 0.5 / q
        else:
            x = R[e + ["BTC"]].loc[:t].tail(180).dropna(axis=1, thresh=160).fillna(0.0); m = x["BTC"]; xi = x.drop(columns="BTC")
            dn = m < m.mean()
            beta = xi.apply(lambda c: np.cov(c, m)[0, 1] / m.var()); bdn = xi[dn].apply(lambda c: np.cov(c, m[dn])[0, 1] / m[dn].var())
            s = bdn if kind == "B" else bdn - beta
            r = s.sort_values(); q = max(len(r) // 5, 1); lo, hi = r.index[:q], r.index[-q:]
            if kind == "B":
                bl, bs = max(beta[hi].mean(), 0.5), max(beta[lo].mean(), 0.5)
                w[hi] += min(0.5 / bl, 1.0) / q; w[lo] -= min(0.5 / bs, 1.0) / q
            else:
                w[hi] += 0.5 / q; w[lo] -= 0.5 / q
        W[t] = w
    return pd.DataFrame(W).T


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    b0 = unit(CS.portfolio_v5(V8)[0]); ref = [shp(b0, "2022", "2026-09-30"), per(b0)]
    C, F = R14.load(); out = {"reference v9.8": ref}
    for k, name in (("A", "A co-skewness (long low)"), ("B", "B downside beta (long high, beta-scaled)"), ("C", "C relative downside beta")):
        W = weights(C, k); h = R14.sleeve(C, F, W).reindex(idx).fillna(0.0)
        b = unit(CS.portfolio_v5(V8.assign(**{name: h}))[0]); r = [shp(b, "2022", "2026-09-30"), per(b)]
        out[name] = {"rebalances": len(W), "sleeve 2022 / 23-24 / 25-26": per(h), "corr with v9.8 (daily)": round(float(dd(h.loc["2022":]).corr(dd(b0))), 3),
                     "book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    (ROOT / "results/v99/r15_coskew.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

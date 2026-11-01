"""v9.9 R17 (research/v99/r17_protocol.json): fee momentum, fees vs price and TVL vs price, cross-sectional, weekly.
Writes results/v99/r17_fundamentals.json."""
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
FD = ROOT / "research_data/defillama_fees"


def fundamentals():
    F, T = {}, {}
    for f in FD.glob("*.parquet"):
        d = pd.read_parquet(f); F[f.stem] = d["fees"]; T[f.stem] = d["tvl"]
    return pd.DataFrame(F).sort_index(), pd.DataFrame(T).sort_index()


def weights(C, kind, FE, TV):
    D = C.resample("1D", label="right", closed="right").last(); W = {}
    for t in [t for t in D.index if t.dayofweek == 0 and t >= pd.Timestamp("2021-12-27")]:
        X = (FE if kind in ("A", "B") else TV).loc[: t - pd.Timedelta(days=1)]               # days before the rebalance day only
        sig = {}
        for c in X.columns:
            if c not in D.columns or not np.isfinite(D.loc[t, c]) or not np.isfinite(D[c].shift(28).loc[t]):
                continue
            x = X[c].dropna()
            if len(x) < 90 or x.index[-1] < t - pd.Timedelta(days=3):
                continue
            if kind == "C":
                a, b = x.iloc[-1], x.loc[: t - pd.Timedelta(days=29)].iloc[-1] if len(x.loc[: t - pd.Timedelta(days=29)]) else np.nan
            else:
                a, b = x.loc[t - pd.Timedelta(days=28):].sum(), x.loc[t - pd.Timedelta(days=56): t - pd.Timedelta(days=29)].sum()
            if not (a > 0 and b > 0):
                continue
            g = np.log(a / b); pr = np.log(D.loc[t, c] / D[c].shift(28).loc[t])
            sig[c] = g if kind == "A" else g - pr
        if len(sig) < 8:
            continue
        s = pd.Series(sig).sort_values(); q = len(s) // 3; w = pd.Series(0.0, index=D.columns)
        w[s.index[:q]] -= 0.5 / q; w[s.index[-q:]] += 0.5 / q; W[t] = w
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
    C, F = R14.load(); FE, TV = fundamentals(); out = {"reference v9.8": ref}
    for k, name in (("A", "A fee momentum"), ("B", "B fees vs price"), ("C", "C TVL vs price")):
        W = weights(C, k, FE, TV); h = R14.sleeve(C, F, W).reindex(idx).fillna(0.0)
        b = unit(CS.portfolio_v5(V8.assign(**{name: h}))[0]); r = [shp(b, "2022", "2026-09-30"), per(b)]
        out[name] = {"rebalances": len(W), "first": str(W.index[0]) if len(W) else None, "mean coins per side": round(float((W > 0).sum(axis=1).mean()), 1) if len(W) else 0,
                     "sleeve 2022 / 23-24 / 25-26": per(h), "corr with v9.8 (daily)": round(float(dd(h.loc["2022":]).corr(dd(b0))), 3),
                     "book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    (ROOT / "results/v99/r17_fundamentals.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

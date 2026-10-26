"""Gen442 (config/gen442_protocol.json): fade non-listing pumps on mid caps. Writes results/gen442.json."""
import glob
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
from qpl.lab import binance_pack as B
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0]); REF = (shp(v96), per(v96))
exclude = set(B.coins()) | {p.name[:-len("USDT_1h.parquet")] for p in (ROOT / "research_data/binance_extra").glob("*USDT_1h.parquet")}
DATA, QD = {}, {}
for s in LL.symbols():
    c = s[:-4]
    k, f = LL._read(s)
    if k is None or len(k) < 24 * 90:
        continue
    DATA[c] = (k, f); QD[c] = k["quote_volume"].resample("1D").sum()
for c in exclude:                                                      # big coins count for the ranking only
    try:
        QD[c] = (B.k5(c).quote_volume.resample("1D").sum() if c in B.coins() else pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["quote_volume"].astype(float).resample("1D").sum())
    except Exception:
        pass
Q = pd.DataFrame(QD).loc[:END]; age = Q.notna().cumsum(); v30 = Q.rolling(30, min_periods=20).sum().shift(1)
rank = v30.where(age.shift(1) >= 60).rank(axis=1, ascending=False); midcap = (rank > 20) & (rank <= 150)
EV = []
for c, (k, f) in DATA.items():
    if c in exclude or c not in midcap:
        continue
    cl, qv = k["close"], k["quote_volume"]
    r24 = cl / cl.shift(24) - 1; v24 = qv.rolling(24).sum(); avg = qv.rolling(24 * 30, min_periods=24 * 20).sum().shift(24) / 30
    ok = (r24 > 0.40) & (v24 > 5 * avg) & midcap[c].reindex(cl.index.floor("D")).fillna(False).to_numpy()
    for t in cl.index[ok.fillna(False).to_numpy()]:
        if t >= pd.Timestamp("2021-06-01"):
            EV.append((c, t))
def sleeve(H):
    P = {}
    for c, t in sorted(EV, key=lambda e: e[1]):
        k, f = DATA[c]; cl = k["close"]
        cc = cl.loc[t:t + pd.Timedelta(days=H)]
        if len(cc) < 2:
            continue
        hit = cc[cc >= cc.iloc[0] * 1.30].index
        last = hit[0] if len(hit) else t + pd.Timedelta(days=H) - pd.Timedelta(hours=1)
        p = pd.Series(-0.05, index=cl.loc[t:last].index); p.index = p.index + pd.Timedelta(hours=1); p = p.reindex(idx).fillna(0.0)
        p = p.where(cl.reindex(idx - pd.Timedelta(hours=1)).notna().to_numpy(), 0.0)
        cur = P.get(c, pd.Series(0.0, index=idx)); P[c] = cur.where(cur != 0, p)
    Pdf = pd.DataFrame(P); g = Pdf.abs().sum(axis=1); Pdf = Pdf.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
    out = pd.Series(0.0, index=idx)
    for c in Pdf.columns:
        k, f = DATA[c]; p = Pdf[c]; cl = k["close"]
        r = (cl / cl.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 / 1e4
    return out
out = {"reference v9.6 A..Z": [REF[0], REF[1]], "events": len(EV), "events per year": {str(y): int(n) for y, n in pd.Series([e[1].year for e in EV]).value_counts().sort_index().items()}, "trials": {}}
for k, H in (("A hold 7 days", 7), ("B hold 3 days", 3)):
    s = sleeve(H); b = unit(CS.portfolio_v5(V6.assign(**{"midcap pump fade": s}))[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"sleeve": per(s), "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)}, "corr listing short": round(float(dd(s).corr(dd(ls))), 2),
                        "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
    print(k, out["trials"][k], flush=True)
(ROOT / "results/gen442.json").write_text(json.dumps(out, indent=1)); print(out["events"], out["events per year"])

"""Gen326 (config/gen326_protocol.json): the Gen316/322 invvol, tranched premium carry on a point-in-time top-K universe (K = 100 / 150)
by trailing 30-day volume, delisted perps included (research_data/binance_pit; loaders from Gen321). Judged vs v8.6 AND vs the
K = 60 reconstruction on the same code (3.121 without pit data). Writes results/gen326.json (results/gen326_codecheck.json without pit data)."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
from qpl.lab import binance_pack as B, extra_pack as X
END = L.END; PIT = L.ROOT / "research_data/binance_pit"
TRADFI = set(json.load(open(L.ROOT / "config/tradfi_perps.json"))["symbols"]) if (L.ROOT / "config/tradfi_perps.json").exists() else set()   # 2026-10-25: stock / commodity perps are not crypto
pit = sorted(c for c in (p.stem.replace("USDT_1h", "") for p in PIT.glob("*USDT_1h.parquet")) if c not in TRADFI) if PIT.exists() else []


def series(c):
    """hourly close, hourly quote volume, hourly premium, funding (8h) for any coin."""
    if c in B.coins():
        k = B.k5(c); return (k.close.resample("1h").last(), k.quote_volume.resample("1h").sum(), B.premium(c)["close"], B.funding(c))
    if c in X.coins():
        d = pd.read_parquet(X.PACK / f"{c}USDT_1h.parquet")
        return (X.close_1h(c), d["quote_volume"].astype(float), X.premium(c), X.funding(c))
    d = pd.read_parquet(PIT / f"{c}USDT_1h.parquet"); d.index = pd.DatetimeIndex(d.index)
    pr = pd.read_parquet(PIT / f"{c}USDT_premium_1h.parquet") if (PIT / f"{c}USDT_premium_1h.parquet").exists() else None
    pr = pr.set_index(pd.to_datetime(pr["time"]))["close"].astype(float) if pr is not None else pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    fu = pd.read_parquet(PIT / f"{c}USDT_funding.parquet") if (PIT / f"{c}USDT_funding.parquet").exists() else None
    fu = fu.set_index(pd.to_datetime(fu["time"]))["last_funding_rate"].astype(float) if fu is not None else pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    return d["close"].astype(float), d["quote_volume"].astype(float), pr, fu


coins = sorted(set(B.coins()) | set(X.coins()) | set(pit))
S = {c: series(c) for c in coins}
H = pd.DataFrame({c: s[0] for c, s in S.items()}).sort_index().loc["2020-01-01":END + " 23:00"]
QV = pd.DataFrame({c: s[1] for c, s in S.items()}).reindex(H.index).resample("1D").sum()
P = H.resample("1D").last(); listed = P.notna().cumsum() >= 60; live = P.notna() & P.ffill().notna()
mon = QV.rolling(30, min_periods=20).sum().where(listed & live)
prem = pd.DataFrame({c: S[c][2].resample("1D").mean() for c in coins}).reindex(P.index).rolling(7).mean()
r = H.pct_change(fill_method=None).fillna(0.0)
F = pd.DataFrame({c: S[c][3] for c in coins}); F.index = F.index - pd.Timedelta(hours=1); F = F.groupby(level=0).sum().reindex(H.index).fillna(0.0)


def sleeve(K):
    uni = mon.rank(axis=1, ascending=False).le(K)
    rk = (-prem).where(uni).rank(axis=1, pct=True); iv = (1 / P.pct_change(fill_method=None).rolling(30).std()).where(uni)
    wl, ws = iv.where(rk > 2 / 3, 0.0), iv.where(rk <= 1 / 3, 0.0)
    w = CS._hold(wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0), 7, True)          # Gen322 tranches
    wd = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)
    held = wd.reindex(H.index.floor("D")).set_axis(H.index).fillna(0.0).where(H.ffill().notna(), 0.0)
    turn = wd.fillna(0.0).diff().abs().sum(axis=1).reindex(H.index.floor("D")).set_axis(H.index).where(H.index.hour == 0, 0.0)
    return (held * r).sum(axis=1) - (held * F).sum(axis=1) - turn.fillna(0.0) * 5 / 1e4, float(uni.sum(axis=1).loc["2021":].mean())


import os
REF = L.REF                                                                   # v8.6 (QPL_REF=v8.6 default); fallback base via QPL_REF
out = {"pit coins available": len(pit), "reference": [round(REF[0], 3), np.round(REF[1], 3).tolist()]}
base = [a for a in L.ALTK if a.name != "premium carry 60"]
for K, nm in ((60, "check K=60 (no pit data: must equal the reference)"), (100, "A top-100"), (150, "B top-150")):
    h, n = sleeve(K); h = h.reindex(L.H6.index).fillna(0.0).rename("premium carry 60")
    b = L.CS.portfolio_v5(pd.concat([L.H6, L.RIDGE] + base + [h], axis=1).fillna(0.0))[0]
    B1, k = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
    out[nm] = {"mean universe size": round(n, 1), "book": [round(B1, 3), np.round(k, 3).tolist()],
               "pass (strict: every period up, +0.05)": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
    print(nm, out[nm], flush=True)
json.dump(out, open(L.ROOT / ("results/gen326.json" if pit else "results/gen326_codecheck.json"), "w"), indent=1)

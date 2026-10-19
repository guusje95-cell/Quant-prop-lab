"""Gen105 checks (descriptive, no selection): components, thresholds, hold, per coin, entry delay, FX lag 2 days, placebo, and the
composite inside the book under each variant. Writes results/gen105_check.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen105_demand.py")}
src = open(ROOT / "scripts/gen105_demand.py").read()
exec(src.split("w = pd.DataFrame(0.0, index=pd.DataFrame(ZC).index")[0] + src[src.index("def book(p):"):src.index("b0, H0 = book(pos)")], g)
CB, B, ZC, ZK, R, pos, IDX, book, per, sh, fx, MORE, END = (g[k] for k in ("CB", "B", "ZC", "ZK", "R", "pos", "IDX", "book", "per", "sh", "fx", "MORE", "END"))
idx1 = IDX.append(pd.DatetimeIndex([IDX[-1] + pd.Timedelta(hours=1)]))


def composite(zc, zk, mode="both"):
    s = {"both": pd.concat([zc, zk], axis=1).mean(axis=1, skipna=False), "coinbase": zc, "kimchi": zk}[mode]
    return (s - s.rolling(30, min_periods=20).mean()) / s.rolling(30, min_periods=20).std()


def weights(th=1.0, mode="both", coins=("BTC", "ETH"), zk_src=None, hold=1, shuffle=None):
    zk_src = zk_src or ZK
    w = pd.DataFrame(0.0, index=pd.DataFrame(ZC).index, columns=CB.CFD)
    for c in coins:
        Z = composite(ZC[c], zk_src[c], mode).reindex(w.index)
        if shuffle is not None:
            Z = pd.Series(Z.to_numpy()[shuffle], index=Z.index)
        s = pd.Series(np.where(Z > th, 0.5, np.where(Z < -th, -0.5, 0.0)), index=w.index)
        if hold > 1:
            s = s.replace(0.0, np.nan).ffill(limit=hold - 1).fillna(0.0)
        w[c] = s.to_numpy()
    return w


def run(lag=0, **kw):
    p = CB.d2h(weights(**kw), idx1)
    if lag:
        p = p.shift(lag).fillna(0.0)
    bk, H = book({**pos, "coinbase premium": p})
    s = per(H["coinbase premium"])
    return {"sleeve DEV": s[0], "sleeve TEST": s[1], "sleeve HOLD": s[2], "sleeve 2020-26": sh(H["coinbase premium"], "2020-01-01", "2026-09-30"),
            "book 2022-26": sh(bk, "2022-01-01", "2026-09-30")}


# FX lagged 2 days (extra safety on timing)
ZK2 = {}
for c in ("BTC", "ETH"):
    bn = B.k5(c).close.resample("1h").last(); up = pd.read_parquet(MORE / f"upbit_KRW-{c}_1h.parquet")["close"]
    fxh = fx.shift(2).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:END]; kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    ZK2[c] = (kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()
rows = []
for nm, kw in (("composite z>1 (adopt candidate)", {}), ("Coinbase only, re-z-scored", {"mode": "coinbase"}), ("kimchi only, re-z-scored", {"mode": "kimchi"}),
               ("z>0.75", {"th": 0.75}), ("z>1.25", {"th": 1.25}), ("z>1.5", {"th": 1.5}), ("hold 2 days", {"hold": 2}),
               ("BTC only", {"coins": ("BTC",)}), ("ETH only", {"coins": ("ETH",)}), ("entry 1h late", {"lag": 1}), ("entry 4h late", {"lag": 4}),
               ("FX lagged 2 days", {"zk_src": ZK2})):
    r = {"variant": nm, **run(**kw)}; rows.append(r); print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
rng = np.random.default_rng(5); n = len(pd.DataFrame(ZC).index); base = rows[0]["sleeve 2020-26"]; sims = []
for _ in range(100):
    blocks = np.arange(n) // 30; order = rng.permutation(blocks.max() + 1)
    perm = np.concatenate([np.where(blocks == b)[0] for b in order])[:n]
    sims.append(run(shuffle=perm)["sleeve 2020-26"])
sims = np.array(sims)
rows.append({"variant": "placebo: 30-day blocks shuffled (100)", "sleeve 2020-26": float(sims.mean()), "p95": float(np.percentile(sims, 95)), "p-value": float((sims >= base).mean())})
print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen105_check.csv", index=False)

# ---- strict FX dating: Yahoo stamps the London day at London midnight (23:00 UTC in summer); date each bar by its London day,
# then use only the previous London day's close (known before day D starts anywhere)
fx_raw = pd.read_parquet(MORE / "yahoo_USDKRW_1d.parquet")["close"]
fx_ld = fx_raw.copy(); fx_ld.index = (pd.DatetimeIndex(fx_ld.index) + pd.Timedelta(hours=2)).normalize()
fx_ld = fx_ld[~fx_ld.index.duplicated(keep="last")]
ZKs = {}
for c in ("BTC", "ETH"):
    bn = B.k5(c).close.resample("1h").last(); up = pd.read_parquet(MORE / f"upbit_KRW-{c}_1h.parquet")["close"]
    fxh = fx_ld.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:END]; kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    ZKs[c] = (kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()
for nm, kw in (("STRICT FX: composite z>1", {"zk_src": ZKs}), ("STRICT FX: kimchi only", {"zk_src": ZKs, "mode": "kimchi"}),
               ("STRICT FX: composite z>0.75", {"zk_src": ZKs, "th": 0.75}), ("STRICT FX: composite z>1.25", {"zk_src": ZKs, "th": 1.25})):
    r = {"variant": nm, **run(**kw)}; rows.append(r); print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen105_check.csv", index=False)

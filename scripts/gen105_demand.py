"""Gen105 (config/gen105_protocol.json): demand composite in the BrightFunded CFD book. Writes results/gen105.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import cfd_book as CB
from qpl.lab import binance_pack as B
END = "2026-09-30 23:00"; MORE = ROOT / "research_data/more"
R, pos, daily = CB.positions()
R = R.loc[:END]; IDX = R.index
fx = pd.read_parquet(MORE / "yahoo_USDKRW_1d.parquet")["close"]; fx.index = pd.DatetimeIndex(fx.index).normalize()
ZC, ZK = {}, {}
for c in ("BTC", "ETH"):
    bn = B.k5(c).close.resample("1h").last()
    cb = CB.coinbase(f"{c}-USD"); prem = (cb / bn - 1).dropna().loc[:END]
    p24 = prem.rolling(24, min_periods=20).mean()
    ZC[c] = ((p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()).resample("1D").last()
    up = pd.read_parquet(MORE / f"upbit_KRW-{c}_1h.parquet")["close"]
    fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:END]; kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    ZK[c] = (kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()
w = pd.DataFrame(0.0, index=pd.DataFrame(ZC).index, columns=CB.CFD)
for c in ("BTC", "ETH"):
    s = pd.concat([ZC[c], ZK[c]], axis=1).mean(axis=1, skipna=False)
    Z = (s - s.rolling(30, min_periods=20).mean()) / s.rolling(30, min_periods=20).std()
    w[c] = np.where(Z > 1, 0.5, np.where(Z < -1, -0.5, 0.0))
idx1 = IDX.append(pd.DatetimeIndex([IDX[-1] + pd.Timedelta(hours=1)]))
pos_new = CB.d2h(w, idx1)


def book(p):
    H = pd.DataFrame({s: CB.sleeve_pnl(p[s], R) for s in CB.SLEEVES}).fillna(0.0)
    ph, W, m = CS.portfolio_v5(H); idx = ph.index
    Wh = W.reindex(idx.floor("D")).set_axis(idx); mh = m.reindex(idx.floor("D")).set_axis(idx)
    net = sum(p[s].reindex(idx).fillna(0.0) * Wh[s].to_numpy()[:, None] for s in CB.SLEEVES).mul(mh * 0.885, axis=0)
    capf = ((5 / 1.5) / net.abs().sum(axis=1)).clip(upper=1).fillna(1.0)
    return ph * capf, H


def sh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().reindex(pd.date_range(a, b)).fillna(0.0); return float(d.mean() / d.std() * np.sqrt(365))


per = lambda h, d0="2020-01-01": (sh(h, d0, "2022-12-31"), sh(h, "2023-01-01", "2024-12-31"), sh(h, "2025-01-01", "2026-09-30"))
b0, H0 = book(pos); b1, H1 = book({**pos, "coinbase premium": pos_new})
s0, s1 = per(H0["coinbase premium"]), per(H1["coinbase premium"]); k0, k1 = per(b0, "2022-01-01"), per(b1, "2022-01-01")
r = {"sleeve old DEV/TEST/HOLD": np.round(s0, 3).tolist(), "sleeve composite DEV/TEST/HOLD": np.round(s1, 3).tolist(),
     "book old 2022-26": sh(b0, "2022-01-01", "2026-09-30"), "book new 2022-26": sh(b1, "2022-01-01", "2026-09-30"),
     "book old TEST/HOLD": np.round(k0[1:], 3).tolist(), "book new TEST/HOLD": np.round(k1[1:], 3).tolist(),
     "corr old/new sleeve": float(pd.concat([H0["coinbase premium"], H1["coinbase premium"]], axis=1).groupby(IDX.floor("D")).sum().corr().iloc[0, 1])}
r["pass"] = bool(s1[0] > 0 and s1[1] >= s0[1] and s1[2] >= s0[2] and r["book new 2022-26"] > r["book old 2022-26"] and k1[1] >= k0[1] and k1[2] >= k0[2])
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame([r]).to_csv(ROOT / "results/gen105.csv", index=False)

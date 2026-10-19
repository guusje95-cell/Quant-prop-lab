"""Gen102 (config/gen102_protocol.json, registered before the data was downloaded). Writes results/gen102.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen88_coinbase.py")}
exec(open(ROOT / "scripts/gen88_coinbase.py").read().split("ROWS, CANDS = [], {}")[0], g)
CS, B, CFD, fhp, d2h, IDX, dsh, G90, q1 = (g[k] for k in ("CS", "B", "CFD", "fhp", "d2h", "IDX", "dsh", "G90", "q1"))
END = "2026-09-30 23:00"; MORE = ROOT / "research_data/more"
hq, wq = q1(1.0)
BOOK = {**G90, "coinbase premium": hq}                                   # current CFD book (C*, Weiss, bounce, Coinbase premium)
bk = lambda cols: CS.portfolio_v5(pd.DataFrame(cols).fillna(0.0))[0]
B0 = dsh(bk(BOOK), "2022-01-01", "2026-09-30"); print("current CFD book 2022-26", round(B0, 3), flush=True)
cst = BOOK["C*"].groupby(IDX.floor("D")).sum()
per = lambda h, d0="2020-01-01": (dsh(h, d0, "2022-12-31"), dsh(h, "2023-01-01", "2024-12-31"), dsh(h, "2025-01-01", "2026-09-30"))
ROWS = []


def zscore_daily(prem_hourly):
    p24 = prem_hourly.rolling(24, min_periods=20).mean()
    m = p24.rolling(720, min_periods=480).mean(); s = p24.rolling(720, min_periods=480).std()
    return ((p24 - m) / s).resample("1D").last()


def sig_w(z, coins, th=1.0, sign=1.0):
    w = pd.DataFrame(0.0, index=z.index, columns=CFD)
    for c in coins:
        w[c] = sign * np.where(z[c] > th, 0.5, np.where(z[c] < -th, -0.5, 0.0))
    return w


def report(name, h, primary, d0="2020-01-01", extra=None):
    p = per(h, d0); bA = dsh(bk({**BOOK, name: h}), "2022-01-01", "2026-09-30")
    r = {"test": name, "DEV": p[0], "TEST": p[1], "HOLD": p[2], "corr C*": float(pd.concat([cst, h.groupby(IDX.floor("D")).sum()], axis=1).loc["2020":].corr().iloc[0, 1]),
         "book before": B0, "book after": bA, **(extra or {})}
    r["pass"] = bool(primary and p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and bA > B0)
    ROWS.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


# P1 Coinbase premium on altcoins
ALTS = ["LTC", "XRP", "ADA", "DOGE", "SOL", "DOT", "AVAX", "LINK", "BCH"]
Z = {}
for c in ALTS:
    cb = pd.read_parquet(ROOT / f"research_data/coinbase/{c}-USD_1h.parquet")["close"]
    bn = B.k5(c).close.resample("1h").last()
    Z[c] = zscore_daily((cb / bn - 1).dropna().loc[:END])
za = pd.DataFrame(Z)
report("P1 Coinbase premium on 9 CFD altcoins (PRIMARY)", fhp(d2h(sig_w(za, ALTS)), 3.3).reindex(IDX).fillna(0.0), True,
       extra={"coins with data": int(za.notna().any().sum())})
# P2 kimchi premium
fx = pd.read_parquet(MORE / "yahoo_USDKRW_1d.parquet")["close"]; fx.index = pd.DatetimeIndex(fx.index).normalize()
ZK = {}
for c in ("BTC", "ETH"):
    up = pd.read_parquet(MORE / f"upbit_KRW-{c}_1h.parquet")["close"]; up.index = pd.DatetimeIndex(up.index).tz_localize(None) if up.index.tz else up.index
    bn = B.k5(c).close.resample("1h").last()
    fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)       # previous day's FX close
    kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:END]
    kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    ZK[c] = (kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()
    print(f"  kimchi premium {c}: median {kd.median() * 1e4:.0f} bp, 1-99% {kd.quantile(0.01) * 1e4:.0f}..{kd.quantile(0.99) * 1e4:.0f} bp, days {len(kd)}", flush=True)
zk = pd.DataFrame(ZK)
report("P2 kimchi premium momentum (PRIMARY)", fhp(d2h(sig_w(zk, ["BTC", "ETH"])), 3.3).reindex(IDX).fillna(0.0), True)
report("P2b kimchi premium contrarian (variant)", fhp(d2h(sig_w(zk, ["BTC", "ETH"], sign=-1.0)), 3.3).reindex(IDX).fillna(0.0), False)
# P3 Fear & Greed
fg = pd.read_parquet(MORE / "fear_greed_1d.parquet")["value"]; fg.index = pd.DatetimeIndex(fg.index).normalize()
fg = fg[~fg.index.duplicated()].sort_index()
s = (fg <= 20).reindex(pd.date_range("2018-02-01", "2026-09-30")).fillna(False)
w = pd.DataFrame(0.0, index=s.index, columns=CFD)
for c in ("BTC", "ETH"):
    w[c] = s.astype(float).rolling(3, min_periods=1).max().to_numpy() * 0.5
report("P3 Fear & Greed <= 20 -> long 3 days (PRIMARY)", fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0), True, extra={"signal days": int(s.loc["2020":].sum())})
# P4 Bitstamp replication of Q1
ZB = {}
for c, pair in (("BTC", "btcusd"), ("ETH", "ethusd")):
    bs = pd.read_parquet(MORE / f"bitstamp_{pair}_1h.parquet")["close"]
    bn = B.k5(c).close.resample("1h").last()
    ZB[c] = zscore_daily((bs / bn - 1).dropna().loc[:END])
zb = pd.DataFrame(ZB)
hb = fhp(d2h(sig_w(zb, ["BTC", "ETH"])), 3.3).reindex(IDX).fillna(0.0)
report("P4 Bitstamp replication of Q1 (check only)", hb, False,
       extra={"corr with Coinbase Q1": float(pd.concat([hq.groupby(IDX.floor("D")).sum(), hb.groupby(IDX.floor("D")).sum()], axis=1).corr().iloc[0, 1])})
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen102.csv", index=False)
print("done", flush=True)

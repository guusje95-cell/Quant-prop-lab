"""Gen84 (config/gen84_protocol.json): MAX effect, idiosyncratic vol, turn-of-month, DVOL VRP overlay.
Writes results/gen84.csv and results/cache_gen84_hourly.parquet."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B

warnings.filterwarnings("ignore")
C = B.coins(); END = "2026-09-30"
P = B.panel("close", "1D", C).loc[:END]; R = P.pct_change(fill_method=None)
listed = P.notna().cumsum() >= 60
MON = pd.Series(P.index.dayofweek == 6, index=P.index)          # decided at Sunday close, held from Monday 00:00
ROWS, CANDS = [], {}


def tercile_ls(score):
    rk = score.where(listed).rank(axis=1, pct=True)
    w = (rk <= 1 / 3).astype(float).div((rk <= 1 / 3).sum(axis=1), axis=0) * 0.5 - (rk > 2 / 3).astype(float).div((rk > 2 / 3).sum(axis=1), axis=0) * 0.5
    return w.where(MON, np.nan).ffill().fillna(0.0)


def dsh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().loc[a:b]
    return float(d.mean() / d.std() * np.sqrt(365)) if d.std() > 0 else np.nan


def mdd(h, a="2022", b="2026-09"):
    d = h.groupby(h.index.floor("D")).sum().loc[a:b]; eq = (1 + d).cumprod(); return float((eq / eq.cummax() - 1).min())


H5 = CS.v5_sleeves(); V5, _, _ = CS.portfolio_v5(H5)
cst = H5["C*"].groupby(H5.index.floor("D")).sum()
base = dsh(V5, "2022", "2026-09"); print("v5 2022-26 Sharpe", round(base, 3), flush=True)


def row(name, h, primary):
    hd = h.groupby(h.index.floor("D")).sum()
    plus, _, _ = CS.portfolio_v5(pd.concat([H5, h.rename(name)], axis=1).fillna(0.0))
    r = {"test": name, "primary": primary, "DEV 2020-22": dsh(h, "2020", "2022"), "TEST 2023-24": dsh(h, "2023", "2024"),
         "HOLD 2025-26": dsh(h, "2025", "2026-09"), "corr C*": float(pd.concat([cst, hd], axis=1).loc["2020":].corr().iloc[0, 1]),
         "v5": base, "v5 + sleeve": dsh(plus, "2022", "2026-09")}
    r["pass"] = bool(primary and r["DEV 2020-22"] > 0 and r["TEST 2023-24"] >= 0.8 and r["HOLD 2025-26"] >= 0.5 and r["corr C*"] <= 0.3 and r["v5 + sleeve"] > base)
    ROWS.append(r); CANDS[name] = h; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


# M: MAX effect (long low-MAX, short high-MAX)
for n, nm, pr in ((7, "M1 MAX 7d (PRIMARY)", True), (30, "M2 MAX 30d", False)):
    row(nm, CS._from_daily_weights(tercile_ls(R.rolling(n).max()), C, 5), pr)

# I: idiosyncratic vol vs BTC, 30 days
rb = R["BTC"]; beta = R.rolling(30).cov(rb).div(rb.rolling(30).var(), axis=0)
alpha = R.rolling(30).mean() - beta.mul(rb.rolling(30).mean(), axis=0)
res2 = {}
iv = pd.DataFrame(index=R.index, columns=C, dtype=float)
for c in C:
    if c == "BTC":
        continue
    e = R[c] - alpha[c].shift(0) - beta[c] * rb      # in-window residual using the window's own fit (end-of-window coefficients)
    iv[c] = e.rolling(30).std()
row("I1 IVOL 30d (PRIMARY)", CS._from_daily_weights(tercile_ls(iv), C, 5), True)

# T: turn of month, long BTC+ETH from close of day (last-1) to close of day 3
d = P.index; last = d.to_period("M").to_timestamp("M")
dom = d.day; days_left = (last - d).days
w = pd.DataFrame(0.0, index=P.index, columns=C)
hold = (days_left <= 1) | (dom <= 2)          # row d = decided at close of d, held during d+1: holds days last, 1, 2, 3
w.loc[hold, ["BTC", "ETH"]] = 0.5
row("T1 turn-of-month BTC/ETH (PRIMARY)", CS._from_daily_weights(w, C, 5), True)

# V: DVOL VRP overlay on v5
dv = pd.read_parquet(ROOT / "data/raw/deribit/BTC_DVOL.parquet")["close"] / 100; dv.index = pd.DatetimeIndex(dv.index).tz_localize(None).normalize()
rv = rb.rolling(30).std() * np.sqrt(365)
vrp = (dv.reindex(P.index) - rv).shift(1)                          # known at the start of day t
lo = vrp.rolling(365, min_periods=180).quantile(1 / 3).shift(1); hi = vrp.rolling(365, min_periods=180).quantile(2 / 3).shift(1)
f = pd.Series(1.0, index=P.index).where(~(vrp > hi), 1.25).where(~(vrp < lo), 0.75).where(lo.notna(), 1.0)
ov = V5 * f.reindex(V5.index.floor("D")).set_axis(V5.index)
r = {"test": "V1 DVOL VRP overlay on v5 (PRIMARY)", "primary": True, "TEST 2023-24": dsh(ov, "2023", "2024"), "HOLD 2025-26": dsh(ov, "2025", "2026-09"),
     "v5": base, "v5 + sleeve": dsh(ov, "2022", "2026-09"), "v5 TEST": dsh(V5, "2023", "2024"), "v5 HOLD": dsh(V5, "2025", "2026-09"),
     "maxdd v5": mdd(V5), "maxdd overlay": mdd(ov)}
r["pass"] = bool(r["TEST 2023-24"] > r["v5 TEST"] and r["HOLD 2025-26"] > r["v5 HOLD"] and r["v5 + sleeve"] > base and r["maxdd overlay"] >= r["maxdd v5"])
ROWS.append(r); CANDS[r["test"]] = ov; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)

pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen84_hourly.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen84.csv", index=False)
print("done", flush=True)

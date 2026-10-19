"""Gen109 (config/gen109_protocol.json): ML in v6. Writes results/gen109.csv."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
END = "2026-09-30"
H5 = CS.v5_sleeves(); H6 = pd.concat([H5, CS.delev_bounce().rename("delev bounce")], axis=1).fillna(0.0)


def sh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().reindex(pd.date_range(a, b)).fillna(0.0); return float(d.mean() / d.std() * np.sqrt(365))


per = lambda h, d0: (sh(h, d0, "2022-12-31"), sh(h, "2023-01-01", "2024-12-31"), sh(h, "2025-01-01", "2026-09-30"))
V6 = CS.portfolio_v5(H6)[0]; k0 = per(V6, "2022-01-01"); B0 = sh(V6, "2022-01-01", "2026-09-30")
cst = H5["C*"].groupby(H5.index.floor("D")).sum(); rows = []


def report(name, h):
    p = per(h, "2021-01-01"); v = CS.portfolio_v5(pd.concat([H6, h.rename(name)], axis=1).fillna(0.0))[0]; k1 = per(v, "2022-01-01")
    r = {"test": name, "DEV 2021-22": p[0], "TEST": p[1], "HOLD": p[2], "corr C*": float(pd.concat([cst, h.groupby(h.index.floor("D")).sum()], axis=1).loc["2021":].corr().iloc[0, 1]),
         "v6 before": B0, "v6 after": sh(v, "2022-01-01", "2026-09-30"), "v6 TEST/HOLD before": np.round(k0[1:], 3).tolist(), "v6 TEST/HOLD after": np.round(k1[1:], 3).tolist()}
    r["pass"] = bool(p[0] > 0 and p[1] >= 0.8 and p[2] >= 0.5 and r["corr C*"] <= 0.3 and r["v6 after"] > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
    rows.append(r); print({k: (round(v_, 3) if isinstance(v_, float) else v_) for k, v_ in r.items()}, flush=True)


# X1
P = pd.read_parquet(ROOT / "results/gen108_preds.parquet")
w = P.pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
report("X1 Gen108 ridge in v6 (perp)", CS._from_daily_weights(w, ["BTC", "ETH"], 5).loc[:END + " 23:00"])
# X2 cross-sectional
C = B.coins(); Pd = B.panel("close", "1D", C).loc[:END]; Rd = Pd.pct_change(fill_method=None)
F = B.funding_panel(C); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D"); FD = F.groupby(level=0).sum().reindex(Pd.index)
prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in C}).reindex(Pd.index)
oi = pd.DataFrame({c: B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1D").last() for c in C}).reindex(Pd.index)
imb = {}
for c in C:
    k = B.k5(c).loc[:END + " 23:55"]; tb = k["taker_buy_volume"].resample("1D").sum(); vv = k["volume"].resample("1D").sum()
    imb[c] = ((2 * tb - vv) / vv)
imb = pd.DataFrame(imb).reindex(Pd.index)
feats = {"r1": Pd / Pd.shift(1) - 1, "r7": Pd / Pd.shift(7) - 1, "r30": Pd / Pd.shift(30) - 1, "vol30": Rd.rolling(30).std(), "fund7": FD.rolling(7).mean(),
         "prem7": prem.rolling(7).mean(), "oi7": oi / oi.shift(7) - 1, "imb7": imb.rolling(7).mean()}
listed = Pd.notna().cumsum() >= 60
rk = {k: v.where(listed).rank(axis=1, pct=True) for k, v in feats.items()}
tgt = (Pd.shift(-7) / Pd - 1).where(listed).rank(axis=1, pct=True)
long = pd.concat({k: v.stack() for k, v in rk.items()}, axis=1); long["y"] = tgt.stack(); long = long.reset_index().rename(columns={"level_0": "day", "level_1": "coin"})
long.columns = ["day", "coin"] + list(rk) + ["y"]
FE = list(rk)
pred = pd.Series(np.nan, index=long.index)
for m in pd.date_range("2021-01-01", END, freq="MS"):
    tr = long[(long["day"] >= "2020-06-01") & (long["day"] < m - pd.Timedelta(days=8))].dropna(subset=["y"])
    te = long[(long["day"] >= m) & (long["day"] < m + pd.offsets.MonthBegin(1))]
    if len(te) == 0 or len(tr) < 500:
        continue
    mdl = Ridge(alpha=10.0).fit(tr[FE].fillna(0.5), tr["y"]); pred.loc[te.index] = mdl.predict(te[FE].fillna(0.5))
long["pred"] = pred
pw = long.pivot(index="day", columns="coin", values="pred").reindex(Pd.index)
rkp = pw.where(listed).rank(axis=1, pct=True)
wx = (rkp > 2 / 3).astype(float).div((rkp > 2 / 3).sum(axis=1), axis=0) * 0.5 - (rkp <= 1 / 3).astype(float).div((rkp <= 1 / 3).sum(axis=1), axis=0) * 0.5
monday = pd.Series(Pd.index.dayofweek == 6, index=Pd.index)
wx = wx.where(monday, np.nan).ffill().fillna(0.0).loc[:END]
wx.loc[:"2020-12-31"] = 0.0
report("X2 cross-sectional ridge, 20 coins (perp)", CS._from_daily_weights(wx, C, 5).loc[:END + " 23:00"])
pd.DataFrame(rows).to_csv(ROOT / "results/gen109.csv", index=False)
print("done", flush=True)

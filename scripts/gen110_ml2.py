"""Gen110 (config/gen110_protocol.json): hourly ridge and pooled altcoin ridge. Writes results/gen110.csv."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import cfd_book as CB
from qpl.lab import binance_pack as B
from qpl.lab.data import stablecoin_caps
END = "2026-09-30"
H5 = CS.v5_sleeves(); H6 = pd.concat([H5, CS.delev_bounce().rename("delev bounce")], axis=1).fillna(0.0)
P = pd.read_parquet(ROOT / "results/gen108_preds.parquet")
wml = P.pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
H7 = pd.concat([H6, CS._from_daily_weights(wml, ["BTC", "ETH"], 5).loc[:END + " 23:00"].rename("ml ridge")], axis=1).fillna(0.0)


def sh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().reindex(pd.date_range(a, b)).fillna(0.0); return float(d.mean() / d.std() * np.sqrt(365))


per = lambda h, d0: (sh(h, d0, "2022-12-31"), sh(h, "2023-01-01", "2024-12-31"), sh(h, "2025-01-01", "2026-09-30"))
V7 = CS.portfolio_v5(H7)[0]; k0 = per(V7, "2022-01-01"); B0 = sh(V7, "2022-01-01", "2026-09-30")
print("v7 candidate", round(B0, 3), np.round(k0[1:], 3), flush=True)
cst = H5["C*"].groupby(H5.index.floor("D")).sum(); rows = []


def report(name, h):
    p = per(h, "2021-01-01"); v = CS.portfolio_v5(pd.concat([H7, h.rename(name)], axis=1).fillna(0.0))[0]; k1 = per(v, "2022-01-01")
    r = {"test": name, "DEV 2021-22": p[0], "TEST": p[1], "HOLD": p[2], "corr C*": float(pd.concat([cst, h.groupby(h.index.floor("D")).sum()], axis=1).loc["2021":].corr().iloc[0, 1]),
         "v7 before": B0, "v7 after": sh(v, "2022-01-01", "2026-09-30"), "v7 TEST/HOLD before": np.round(k0[1:], 3).tolist(), "v7 TEST/HOLD after": np.round(k1[1:], 3).tolist()}
    r["pass"] = bool(p[0] > 0 and p[1] >= 0.8 and p[2] >= 0.5 and r["corr C*"] <= 0.3 and r["v7 after"] > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
    rows.append(r); print({k: (round(v_, 3) if isinstance(v_, float) else v_) for k, v_ in r.items()}, flush=True)


def walk(D, feats, horizon_rows=1, by="day", start="2020-03-01"):
    out = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D[by] >= start) & (D[by] < m - pd.Timedelta(days=1))].dropna(subset=["target"])
        te = D[(D[by] >= m) & (D[by] < m + pd.offsets.MonthBegin(1))]
        if len(te) == 0 or len(tr) < 500:
            continue
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=10.0).fit(Xtr, tr["target"]); s = np.std(mdl.predict(Xtr)) or 1.0
        out.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    return out


# ---- H1 hourly
hrs = []
for c in ("BTC", "ETH"):
    k = B.k5(c).loc[:END + " 23:55"]
    cl = k.close.resample("1h").last(); idx = cl.index
    tb = k["taker_buy_volume"].resample("1h").sum(); vv = k["volume"].resample("1h").sum(); imb = (2 * tb - vv) / vv
    pm = B.premium(c)["close"].reindex(idx)
    oi = B.metrics(c)["sum_open_interest_value"]; oi = oi.where(oi > 0).resample("1h").last().reindex(idx).ffill()
    cb = CB.coinbase(f"{c}-USD").reindex(idx); cp = cb / cl - 1
    p24 = cp.rolling(24, min_periods=20).mean(); zc = (p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()
    f = pd.DataFrame({"r1": cl.pct_change(), "r4": cl / cl.shift(4) - 1, "r24": cl / cl.shift(24) - 1, "imb1": imb, "imb4": imb.rolling(4).mean(),
                      "pm1": pm, "pm4": pm.rolling(4).mean(), "oi1": oi / oi.shift(1) - 1, "oi4": oi / oi.shift(4) - 1, "cp": cp, "zc": zc}, index=idx)
    f["is_eth"] = 1.0 if c == "ETH" else 0.0; f["target"] = cl.shift(-4) / cl - 1; f["coin"] = c; f["hour"] = idx
    hrs.append(f)
DH = pd.concat(hrs).reset_index(drop=True)
FH = ["r1", "r4", "r24", "imb1", "imb4", "pm1", "pm4", "oi1", "oi4", "cp", "zc", "is_eth"]
DH["day"] = DH["hour"]                                       # monthly split on the hour stamp; training needs target known: exclude last 4h
DH.loc[:, "pred"] = walk(DH, FH, by="hour")
ph = DH.pivot(index="hour", columns="coin", values="pred").fillna(0.0)
posh = 0.5 * ph.rolling(4, min_periods=1).mean().shift(1).fillna(0.0)   # prediction made at the end of hour t -> held from t+1
R1 = B.panel("close", "1h", ["BTC", "ETH"]).loc[:END + " 23:00"].pct_change(fill_method=None).fillna(0.0)
fund = CS._funding_hourly(["BTC", "ETH"], R1.index); pp = posh.reindex(R1.index).fillna(0.0)
h1 = (pp * R1).sum(axis=1) - (pp * fund).sum(axis=1) - pp.diff().abs().fillna(pp.abs()).sum(axis=1) * 5 / 1e4
report("H1 hourly ridge BTC/ETH (perp)", h1)
# ---- A1 pooled altcoins daily
ALTS = ["LTC", "XRP", "ADA", "DOGE", "SOL", "DOT", "AVAX", "LINK", "BCH"]
days = pd.date_range("2020-01-01", END)
caps = stablecoin_caps(); caps = caps.where(caps > 0); caps.index = pd.DatetimeIndex(caps.index).normalize()
stab = (caps / caps.shift(1) - 1).shift(2).reindex(days)
rws = []
for c in ALTS:
    k = B.k5(c).loc[:END + " 23:55"]; close = k.close.resample("1D").last().reindex(days); ret = close.pct_change()
    f = pd.DataFrame(index=days)
    for n in (1, 3, 7, 30):
        f[f"r{n}"] = close / close.shift(n) - 1
    f["vol7"] = ret.rolling(7).std(); f["vol30"] = ret.rolling(30).std()
    fu = B.funding(c); fd = fu.groupby((fu.index - pd.Timedelta(seconds=1)).floor("D")).sum().reindex(days); f["fund1"] = fd; f["fund7"] = fd.rolling(7).mean()
    pm = B.premium(c)["close"]; f["prem"] = pm.groupby(pm.index.floor("D")).mean().reindex(days)
    oi = B.metrics(c)["sum_open_interest_value"]; oi = oi.where(oi > 0).resample("1D").last().reindex(days); f["oi1"] = oi / oi.shift(1) - 1; f["oi7"] = oi / oi.shift(7) - 1
    tb = k["taker_buy_volume"].resample("1D").sum(); vv = k["volume"].resample("1D").sum(); f["imb"] = ((2 * tb - vv) / vv).reindex(days)
    bn = k.close.resample("1h").last(); cb = pd.read_parquet(ROOT / f"research_data/coinbase/{c}-USD_1h.parquet")["close"]; prem = (cb / bn - 1).dropna()
    p24 = prem.rolling(24, min_periods=20).mean(); zc = (p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()
    f["zc"] = zc.resample("1D").last().reindex(days); f["stab"] = stab
    for a in ALTS:
        f[f"d_{a}"] = 1.0 if a == c else 0.0
    f["target"] = ret.shift(-1); f["coin"] = c; rws.append(f)
DA = pd.concat(rws).reset_index().rename(columns={"index": "day"})
FA = [x for x in DA.columns if x not in ("day", "target", "coin")]
DA["pred"] = walk(DA, FA)
wa = DA.pivot(index="day", columns="coin", values="pred").reindex(days).fillna(0.0) * 0.5 * 2 / 9
report("A1 daily ridge pooled over 9 altcoins (perp)", CS._from_daily_weights(wa, ALTS, 5).loc[:END + " 23:00"])
pd.DataFrame(rows).to_csv(ROOT / "results/gen110.csv", index=False)
print("done", flush=True)

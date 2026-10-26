"""Gen439 (config/gen439_protocol.json): market-wide altcoin froth (funding / premium) as basket members. Writes results/gen439.json."""
import glob
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
import basket_live as BL
from qpl.lab import binance_pack as B
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
TF = set(json.load(open(ROOT / "config/tradfi_perps.json"))["symbols"])
EX = ROOT / "research_data/binance_extra"; PIT = ROOT / "research_data/binance_pit"
QV, FU, PR = {}, {}, {}
def add(c, qv, fu, pr):
    QV[c] = qv.resample("1D").sum(); FU[c] = fu; PR[c] = pr
for c in B.coins():
    f = B.funding(c); add(c, B.k5(c).quote_volume, f.groupby(f.index.floor("D")).mean() * 1.0, B.premium(c)["close"].resample("1D").mean())
for p in EX.glob("*USDT_1h.parquet"):
    c = p.name[:-len("USDT_1h.parquet")]
    if c in QV:
        continue
    k = pd.read_parquet(p); f = pd.read_parquet(EX / f"{c}USDT_funding.parquet"); f.index = pd.to_datetime(f["time"])
    pr = pd.read_parquet(EX / f"{c}USDT_premium_1h.parquet"); pr.index = pd.to_datetime(pr["time"]) if "time" in pr else pd.DatetimeIndex(pr.index)
    sc = 8.0 / f["funding_interval_hours"].astype(float) if "funding_interval_hours" in f else 1.0
    add(c, k["quote_volume"].astype(float), (f["last_funding_rate"] * sc).groupby(f.index.floor("D")).mean(), pr["close"].astype(float).resample("1D").mean())
for p in glob.glob(str(PIT / "*_funding.parquet")):
    s = Path(p).name[:-len("_funding.parquet")]; c = s[:-4]
    if c in TF or c in QV or not (PIT / f"{s}_1h.parquet").exists() or not (PIT / f"{s}_premium_1h.parquet").exists():
        continue
    k = pd.read_parquet(PIT / f"{s}_1h.parquet"); f = pd.read_parquet(p); f.index = pd.to_datetime(f["time"])
    pr = pd.read_parquet(PIT / f"{s}_premium_1h.parquet"); pr.index = pd.to_datetime(pr["time"]) if "time" in pr else pd.DatetimeIndex(pr.index)
    sc = 8.0 / f["funding_interval_hours"].astype(float).clip(lower=1)
    add(c, k["quote_volume"].astype(float), (f["last_funding_rate"] * sc).groupby(f.index.floor("D")).mean(), pr["close"].astype(float).resample("1D").mean())
days = BL.DAYS
Q = pd.DataFrame(QV).reindex(days); Fd = pd.DataFrame(FU).reindex(days); Pd = pd.DataFrame(PR).reindex(days)
age = Q.notna().cumsum(); v30 = Q.rolling(30, min_periods=20).sum().shift(1)
mem = v30.where(age.shift(1) >= 60).rank(axis=1, ascending=False) <= 100
w = v30.where(mem)
def agg(X):
    Xv = X.where(mem); ww = w.where(Xv.notna()); return (Xv * ww).sum(axis=1) / ww.sum(axis=1)
def zz(x):
    x7 = x.rolling(7, min_periods=5).mean(); return ((x7 - x7.rolling(365, min_periods=250).mean()) / x7.rolling(365, min_periods=250).std()).shift(1)
ZF, ZP = zz(agg(Fd)), zz(agg(Pd))
mk = lambda z: (lambda: pd.DataFrame({"BTC": -0.125 * z.clip(-2, 2) / 2, "ETH": -0.125 * z.clip(-2, 2) / 2}).fillna(0.0))
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0]); REF = (shp(v96), per(v96))
bk0, _ = BL.basket(idx); r0 = unit(CS.portfolio_v5(V6.assign(**{"diversifier basket": bk0}))[0]); REF2 = (shp(r0), per(r0))
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
out = {"reference v9.6 (live timing)": [REF[0], REF[1]], "reference rebuilt basket": [REF2[0], REF2[1]], "coins": len(QV), "trials": {}}
base = list(BL.MEMBERS)
for k, z in (("A alt funding froth", ZF), ("B alt premium froth", ZP)):
    BL.BUILD[k] = mk(z); BL.MEMBERS = base + [k]; bk, _ = BL.basket(idx); BL.MEMBERS = base
    m = CS._from_daily_weights(mk(z)().reindex(days).fillna(0.0), ["BTC", "ETH"], 5).reindex(idx).fillna(0.0)
    b = unit(CS.portfolio_v5(V6.assign(**{"diversifier basket": bk}))[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"member": per(m), "corr basket": round(float(dd(m).corr(dd(bk0))), 2), "basket": per(bk), "book": r, "pass": bool(ok(r, REF) and ok(r, REF2))}
    print(k, out["trials"][k], flush=True)
(ROOT / "results/gen439.json").write_text(json.dumps(out, indent=1))

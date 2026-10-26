"""Gen410 (config/gen410_protocol.json): the frozen cascade rule on the point-in-time top-20. Writes results/gen410.json."""
import glob
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen57_cascade_hourly as CH
import listing_live as LL
from qpl.lab import binance_pack as B
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
TF = set(json.load(open(ROOT / "config/tradfi_perps.json"))["symbols"])
PACK = list(B.coins()); EX = ROOT / "research_data/binance_extra"; PIT = ROOT / "research_data/binance_pit"
EXTRA = sorted(p.name[:-len("USDT_1h.parquet")] for p in EX.glob("*USDT_1h.parquet"))
CAND = json.load(open(ROOT / "config/cascade_pit_symbols.json"))["symbols"]
# ---- quote volume of every perp (for the point-in-time ranking)
qv = {}
for c in PACK:
    qv[c] = B.k5(c).quote_volume.resample("1h").sum()
for c in EXTRA:
    qv[c] = pd.read_parquet(EX / f"{c}USDT_1h.parquet")["quote_volume"].astype(float)
for f in glob.glob(str(PIT / "*_1h.parquet")):
    if f.endswith(("premium_1h.parquet", "hl_1h.parquet", "oi_1h.parquet")):
        continue
    s = Path(f).name[:-len("_1h.parquet")]
    if s in TF or not s.endswith("USDT"):
        continue
    c = s[:-4]
    if c not in qv:
        qv[c] = pd.read_parquet(f)["quote_volume"].astype(float)
QD = pd.DataFrame({c: s.resample("1D").sum() for c, s in qv.items()}).loc[:END]
age = QD.notna().cumsum(); vol30 = QD.rolling(30, min_periods=20).sum().shift(1)
first_of_month = ~QD.index.to_period("M").duplicated()
mem = (vol30.where(age.shift(1) >= 60).rank(axis=1, ascending=False) <= 20)[first_of_month].reindex(QD.index).ffill().fillna(False).astype(bool)
# ---- hourly frames for the cascade (c, lo, hi, v, oi), oi masked outside membership
def frame(c):
    if c in PACK:
        d = CH.hourly(c).copy()
    elif c in EXTRA:
        k = pd.read_parquet(EX / f"{c}USDT_1h.parquet"); o = pd.read_parquet(EX / f"{c}USDT_oi_1h.parquet")
        d = pd.DataFrame({"c": k["close"], "lo": k["low"], "hi": k["high"], "v": k["quote_volume"]}).astype(float); d["oi"] = o.iloc[:, 0].astype(float).reindex(d.index)
    else:
        f = PIT / f"{c}USDT_hl_1h.parquet"; g = PIT / f"{c}USDT_oi_1h.parquet"
        if not f.exists() or not g.exists():
            return None
        k = pd.read_parquet(f); d = pd.DataFrame({"c": k["close"], "lo": k["low"], "hi": k["high"], "v": k["quote_volume"]}).astype(float)
        d["oi"] = pd.read_parquet(g)["oi_value"].astype(float).reindex(d.index)
    d.index = pd.DatetimeIndex(d.index)
    m = mem[c].reindex(d.index.floor("D")).fillna(False).to_numpy() if c in mem else np.zeros(len(d), bool)
    d["oi"] = d["oi"].where(m)
    return d
universe = [c for c in mem.columns if mem[c].any()]
missing = []
for c in universe:
    d = frame(c)
    if d is None:
        missing.append(c); continue
    CH.CACHE[c] = d
coins = [c for c in universe if c in CH.CACHE]
cas_pit = CS.cascade(limit=0.005, through=0.001, coins=coins).reindex(idx).fillna(0.0)
for c in list(CH.CACHE):                                           # reset to the original pack frames for the reference
    CH.CACHE.pop(c)
cas_pack = CS.cascade(limit=0.005, through=0.001).reindex(idx).fillna(0.0)
ls, _, _ = LL.pnl(idx)
books = {}
for nm, VV in {"v9.5": V, "v9.6": V.assign(**{"listing short": ls})}.items():
    b0 = unit(CS.portfolio_v5(VV)[0]); b1 = unit(CS.portfolio_v5(VV.assign(**{"cascade limit strict": cas_pit}))[0])
    books[nm] = {"pack cascade": [shp(b0), per(b0)], "point-in-time cascade": [shp(b1), per(b1)], "change": round(shp(b1) - shp(b0), 3)}
out = {"universe ever in the top-20": len(universe), "without data": missing, "members per month (median)": int(mem.sum(axis=1).median()),
       "check: pack cascade vs saved sleeve, max |diff|": float((cas_pack - V["cascade limit strict"]).abs().max()),
       "cascade sleeve pack": per(cas_pack), "cascade sleeve point-in-time": per(cas_pit), "books": books,
       "judgement (protocol, v9.5)": "revise planning down and switch the live cascade" if books["v9.5"]["change"] < -0.10 else "v9.5 / v9.6 cascade stays"}
(ROOT / "results/gen410.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

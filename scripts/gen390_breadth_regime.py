"""Gen390 (config/gen390_protocol.json). Writes results/gen390.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen386_options_attention.py").read().split("ref_book = pd.read_parquet")[0]
g = {"__file__": str(ROOT / "scripts/gen386_options_attention.py")}; exec(compile(src, "g386", "exec"), g)
POOL, daily, z, idx, dd, shp, per, unit, END, CS, base, K1, days = (g[k] for k in ("POOL", "daily", "z", "idx", "dd", "shp", "per", "unit", "END", "CS", "base", "K1", "days"))
from qpl.lab import binance_pack as B
R = {c: B.k5(c).close.resample("1h").last().pct_change().fillna(0.0) for c in ("BTC", "ETH", "SOL")}
FU = {}
for c in R:
    f = B.funding(c).copy(); f.index = f.index - pd.Timedelta(hours=1); FU[c] = f.groupby(level=0).sum()
def pnl_daily(W):
    W = W.reindex(days).fillna(0.0).shift(1); out = 0.0
    for c in W:
        p = W[c].reindex(idx.floor("D")).set_axis(idx).fillna(0.0); r = R[c].reindex(idx).fillna(0.0); f = FU[c].reindex(idx).fillna(0.0)
        out = out + p * r - p * f - p.diff().abs().fillna(0.0) * 5 / 1e4
    return out
C3 = ("BTC", "ETH", "SOL")
NEW = {"A1 top-trader crowding incl. SOL": pd.DataFrame({c: -0.125 * z(daily(B.metrics(c)["count_toptrader_long_short_ratio"], "mean"), 90).clip(-2, 2) / 2 for c in C3}),
       "A2 retail crowding incl. SOL": pd.DataFrame({c: -0.125 * z(daily(B.metrics(c)["count_long_short_ratio"], "mean"), 90).clip(-2, 2) / 2 for c in C3}),
       "A3 leverage build-up incl. SOL": pd.DataFrame({c: -0.125 * z(np.log(daily(B.metrics(c)["sum_open_interest_value"].where(lambda s: s > 0))).diff(7), 90).clip(-2, 2) / 2 for c in C3})}
ac = {}
for c in ("BTC", "ETH"):
    r = B.k5(c).close.resample("1D").last().pct_change().reindex(days)
    rho = r.rolling(90, min_periods=60).apply(lambda x: pd.Series(x).autocorr(1), raw=True)
    ac[c] = (0.125 * np.sign(rho) * np.sign(r) * (rho.abs() > 0.05)).fillna(0.0)          # decided at the close of d (uses r of day d)
NEW["B autocorrelation regime"] = pd.DataFrame(ac)
hr = pd.read_csv(ROOT / "data/raw/ext/coinmetrics-data/csv/btc.csv", usecols=["time", "HashRate"]).dropna(); hr.index = pd.to_datetime(hr.pop("time")); hr = hr["HashRate"].reindex(days).shift(1)
m30, m60 = hr.rolling(30).mean(), hr.rolling(60).mean(); below = (m30 < m60).astype(int)
runlen = below.groupby((below != below.shift()).cumsum()).cumsum()
cross = (m30 > m60) & (below.shift(1) == 1) & (runlen.shift(1) >= 10)
sig = pd.Series(0.0, index=days)
for d in days[cross.fillna(False).to_numpy()]:
    sig.loc[d:d + pd.Timedelta(days=29)] = 0.25
NEW["C hash ribbons"] = pd.DataFrame({"BTC": sig.where(hr.notna(), 0.0)})
for k, w in NEW.items():
    POOL[k] = pnl_daily(w).reindex(idx).fillna(0.0)
ref_book = pd.read_parquet(ROOT / "results/gen385_book_hourly.parquet")["book"]; REF = (shp(ref_book), per(ref_book))
K1d = dd(K1).loc["2022":"2024"]; rows = {}
for nm, h in POOL.items():
    rows[nm] = {"2022": shp(h, "2022", "2022"), "2023-24": shp(h, "2023", "2024"), "2022-24": shp(h, "2022", "2024"),
                "corr K1 2022-24": round(float(pd.concat([dd(h).loc["2022":"2024"], K1d], axis=1).corr().iloc[0, 1]), 3), "2025-26 (record)": shp(h, "2025", END)}
elig = [k for k, v in rows.items() if v["2022"] > 0 and v["2023-24"] > 0 and abs(v["corr K1 2022-24"]) < 0.3]
kept = []
for k in sorted(elig, key=lambda k: -rows[k]["2022-24"]):
    if all(abs(float(pd.concat([dd(POOL[k]), dd(POOL[x])], axis=1).loc["2022":"2024"].corr().iloc[0, 1])) < 0.7 for x in kept):
        kept.append(k)
sdv = pd.DataFrame({k: dd(POOL[k]) for k in kept}).loc["2022":"2024"].std()
bh = sum(POOL[k] / sdv[k] for k in kept); bh = bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
s3 = open(ROOT / "scripts/gen383_ensembles.py").read().split("T = {")[0]; g3 = {"__file__": str(ROOT / "scripts/gen383_ensembles.py")}; exec(compile(s3, "g383", "exec"), g3)
b = unit(CS.portfolio_v5(base.assign(**{"trend 4h": g3["te"], "alt kimchi": g3["ke"], "diversifier basket": bh.reindex(base.index).fillna(0.0)}))[0]); B1, k = shp(b), per(b)
out = {"reference v9.2": [REF[0], REF[1]], "new": {k2: rows[k2] for k2 in NEW}, "kept": kept, "basket": per(bh), "basket 2022-26": shp(bh), "v9.2 structure + new basket": [B1, k],
       "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
bh.to_frame("basket").to_parquet(ROOT / "results/gen390_basket_hourly.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen390_book_hourly.parquet")
(ROOT / "results/gen390.json").write_text(json.dumps(out, indent=1))
for k2, v in out["new"].items(): print(k2, v)
print({k2: v for k2, v in out.items() if k2 != "new"})

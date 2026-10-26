"""Gen458 (config/gen458_protocol.json): v9.7 with a rolling BTC beta hedge. Writes results/gen458.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import binance_pack as B
END = "2026-09-30"
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
b = pd.read_parquet(ROOT / "results/v97_book_hourly.parquet")["book"]; REF = (shp(b), per(b))
r = B.k5("BTC").close.resample("1h").last().pct_change().reindex(b.index).fillna(0.0)
f = B.funding("BTC").copy(); f.index = f.index - pd.Timedelta(hours=1); f = f.groupby(level=0).sum().reindex(b.index).fillna(0.0)
bd, rd = dd(b), dd(r)
beta = (bd.rolling(90, min_periods=60).cov(rd) / rd.rolling(90, min_periods=60).var()).shift(1)
h = -beta.reindex(b.index.floor("D")).set_axis(b.index).fillna(0.0)
hp = h * r - h * f - h.diff().abs().fillna(0.0) * 5 / 1e4
x = unit(b + hp); out = {"reference v9.7": [REF[0], REF[1]], "mean beta": round(float(beta.loc["2022":].mean()), 3), "book hedged": [shp(x), per(x)],
                         "pass": bool(shp(x) >= REF[0] + 0.05 and all(per(x)[i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen458.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))

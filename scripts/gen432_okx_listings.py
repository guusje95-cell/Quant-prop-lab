"""Gen432 (config/gen432_protocol.json, descriptive): the listing effect on OKX. Writes results/gen432.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import listing_live as LL
D = ROOT / "research_data/okx_listings"; ins = json.loads((D / "instruments.json").read_text())
binance = {s[:-4]: t0 for s, t0, c, f in LL.events()}
rows = []
for r in ins:
    f = D / f"{r['instId']}_1h.parquet"
    if not f.exists():
        continue
    k = pd.read_parquet(f); c = k["close"]
    if len(c) < 48:
        continue
    t0 = pd.to_datetime(r["listTime"], unit="ms"); start = (t0 + pd.Timedelta(hours=24)).ceil("D")
    cc = c.loc[start:start + pd.Timedelta(days=30)]
    if len(cc) < 24 * 25:
        continue
    r30 = float(cc.iloc[-1] / cc.iloc[0] - 1)
    hit = cc[cc >= cc.iloc[0] * 1.3].index
    exitp = cc.loc[hit[0]] * 1.001 if len(hit) else cc.iloc[-1]
    short = float(-(exitp / cc.iloc[0] - 1)) - 0.002                    # Gen426 rule, 10 bp each side, before funding
    vol24 = float(k["quote_volume"].loc[t0:t0 + pd.Timedelta(hours=23)].sum())
    b = r["base"].upper(); onb = b in binance and abs((binance[b] - t0).days) <= 7
    rows.append({"base": b, "year": start.year, "r30": r30, "short": short, "vol24": vol24, "binance_same_week": onb})
X = pd.DataFrame(rows)
out = {"listings with 25+ days of data": len(X), "also a Binance listing event within 7 days": int(X.binance_same_week.sum()), "by year": {}}
for y, g in X.groupby("year"):
    out["by year"][str(y)] = {"n": len(g), "median r30": round(float(g.r30.median()), 3), "mean r30": round(float(g.r30.mean()), 3),
                              "Gen426 short mean (no funding)": round(float(g.short.mean()), 3), "share falling": round(float((g.r30 < 0).mean()), 2)}
only = X[~X.binance_same_week]
out["OKX-only events"] = {"n": len(only), "median r30": round(float(only.r30.median()), 3), "Gen426 short mean (no funding)": round(float(only.short.mean()), 3)}
(ROOT / "results/gen432.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))

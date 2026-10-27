"""Entry crowding of every research listing event (Gen461 / Gen468): mean all-account long/short ratio over the 24 h before the
listing-short entry, from the Binance archive metrics (data/lab/binance_vision, local research cache). Writes
config/listing_crowding.json so the paper code needs no 7 GB archive; live listings use <live>/listings/<SYM>_ratios.parquet."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import listing_live as LL
ARCH = ROOT / "data/lab/binance_vision"
out = {}
for s, t0, c, f in LL.events():
    e = (t0 + pd.Timedelta(hours=24)).ceil("D"); m = ARCH / f"{s}_metrics.parquet"
    if not m.exists():
        continue
    x = pd.read_parquet(m, columns=["time", "count_long_short_ratio"]); x["time"] = pd.to_datetime(x["time"])
    v = x[(x["time"] >= e - pd.Timedelta(hours=24)) & (x["time"] < e)]["count_long_short_ratio"].astype(float).dropna()
    if len(v) > 50:
        out[s] = round(float(v.mean()), 4)
(ROOT / "config/listing_crowding.json").write_text(json.dumps({"source": "Binance archive metrics count_long_short_ratio, 24 h before entry", "L": out}, indent=0))
print(len(out))

"""Coinbase hourly candles of the first 6 hours of each R16 event product (public API) -> research_data/coinbase_listings/first_hours.json"""
import json
import sys
import time
from pathlib import Path
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]; sys.path[:0] = [str(ROOT / "scripts/v99"), str(ROOT / "scripts"), str(ROOT / "src")]
import r16_coinbase as R16
D = json.loads((ROOT / "research_data/coinbase_listings/first_trade.json").read_text()); E = R16.events(); out = {}
for pid, p in D.items():
    c = p["base"]
    if c not in E or not p["first_trade_utc"] or pd.Timestamp(p["first_trade_utc"]) != E[c]:
        continue
    t = pd.Timestamp(p["first_trade_utc"]).tz_localize("UTC")
    r = requests.get(f"https://api.exchange.coinbase.com/products/{pid}/candles", params={"start": t.isoformat(), "end": (t + pd.Timedelta(hours=6)).isoformat(), "granularity": 3600}, timeout=30)
    rows = r.json() if r.status_code == 200 else []
    out.setdefault(c, {})[pid] = sorted([[str(pd.Timestamp(x[0], unit="s")), x[4], x[5]] for x in rows])      # time, close, volume
    time.sleep(0.15)
(ROOT / "research_data/coinbase_listings/first_hours.json").write_text(json.dumps(out, indent=0)); print(len(out))

"""First trading hour of every Binance.US USD / USDT pair (public API, no key) -> research_data/binanceus_listings/first_trade.json.
Delisted pairs are not in exchangeInfo (biases against a short)."""
import json
import time
from pathlib import Path
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "research_data/binanceus_listings/first_trade.json"; API = "https://api.binance.us/api/v3"


def get(path, params):
    for i in range(5):
        r = requests.get(API + path, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        time.sleep(2 ** i)
    return None


def main():
    S = [s for s in get("/exchangeInfo", {})["symbols"] if s["quoteAsset"] in ("USD", "USDT")]; out = {}
    for s in S:
        d = get("/klines", {"symbol": s["symbol"], "interval": "1d", "startTime": 0, "limit": 1}); time.sleep(0.1)
        if not d:
            continue
        h = get("/klines", {"symbol": s["symbol"], "interval": "1h", "startTime": d[0][0], "limit": 24}); time.sleep(0.1)
        out[s["symbol"]] = {"base": s["baseAsset"], "quote": s["quoteAsset"], "status": s["status"],
                            "first_trade_utc": str(pd.Timestamp(h[0][0] if h else d[0][0], unit="ms"))}
    OUT.write_text(json.dumps(out, indent=0)); print(len(out))


if __name__ == "__main__":
    main()

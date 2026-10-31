"""First trading hour of every Coinbase Exchange USD / USDT / USDC product (public API, no key) -> research_data/coinbase_listings/first_trade.json.
Daily candles (300 per call) from 2019-01-01 locate the first day, hourly candles of that day the first hour."""
import json
import time
from pathlib import Path
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "research_data/coinbase_listings/first_trade.json"
API = "https://api.exchange.coinbase.com"


def candles(pid, start, end, gran):
    for _ in range(5):
        r = requests.get(f"{API}/products/{pid}/candles", params={"start": start.isoformat(), "end": end.isoformat(), "granularity": gran}, timeout=30)
        if r.status_code == 429:
            time.sleep(1); continue
        return r.json() if r.status_code == 200 else []
    return []


def first_trade(pid):
    t = pd.Timestamp("2019-01-01", tz="UTC"); now = pd.Timestamp.now(tz="UTC")
    while t < now:
        e = min(t + pd.Timedelta(days=299), now); c = candles(pid, t, e, 86400); time.sleep(0.12)
        if c:
            d0 = pd.Timestamp(min(x[0] for x in c), unit="s", tz="UTC")
            h = candles(pid, d0, d0 + pd.Timedelta(hours=24), 3600); time.sleep(0.12)
            return str(pd.Timestamp(min(x[0] for x in h), unit="s") if h else d0.tz_localize(None))
        t = e
    return None


def main():
    P = requests.get(f"{API}/products", timeout=30).json(); done = json.loads(OUT.read_text()) if OUT.exists() else {}
    for p in sorted(P, key=lambda x: x["id"]):
        if p["quote_currency"] not in ("USD", "USDT", "USDC") or p["id"] in done:
            continue
        done[p["id"]] = {"base": p["base_currency"], "quote": p["quote_currency"], "status": p["status"], "first_trade_utc": first_trade(p["id"])}
        if len(done) % 25 == 0:
            OUT.write_text(json.dumps(done, indent=0)); print(len(done), p["id"], done[p["id"]]["first_trade_utc"], flush=True)
    OUT.write_text(json.dumps(done, indent=0)); print("done", len(done))


if __name__ == "__main__":
    main()

"""First trade of every Kraken USD pair (public API, no key): /0/public/Trades?since=0 returns the oldest trades.
-> research_data/kraken_listings/first_trade.json. Delisted pairs are not served (biases against a short of new listings)."""
import json
import time
from pathlib import Path
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "research_data/kraken_listings/first_trade.json"
API = "https://api.kraken.com/0/public"; RENAME = {"XBT": "BTC", "XDG": "DOGE"}


def main():
    P = requests.get(f"{API}/AssetPairs", timeout=30).json()["result"]; done = json.loads(OUT.read_text()) if OUT.exists() else {}
    for k, v in sorted(P.items()):
        alt = v["altname"]
        if not alt.endswith("USD") or v.get("quote") not in ("ZUSD", "USD") or k in done:
            continue
        base = alt[:-3]; base = RENAME.get(base, base)
        for i in range(5):
            r = requests.get(f"{API}/Trades", params={"pair": k, "since": 0, "count": 1}, timeout=30).json()
            if r.get("error") and any("Too many" in e for e in r["error"]):
                time.sleep(5 * (i + 1)); continue
            break
        res = r.get("result") or {}; tr = next((x for kk, x in res.items() if kk != "last"), [])
        done[k] = {"base": base, "altname": alt, "first_trade_utc": str(pd.Timestamp(float(tr[0][2]), unit="s").floor("s")) if tr else None}
        time.sleep(1.1)
        if len(done) % 50 == 0:
            OUT.write_text(json.dumps(done, indent=0)); print(len(done), alt, done[k]["first_trade_utc"], flush=True)
    OUT.write_text(json.dumps(done, indent=0)); print("done", len(done))


if __name__ == "__main__":
    main()

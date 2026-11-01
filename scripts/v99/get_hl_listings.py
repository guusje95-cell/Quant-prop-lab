"""First funding record of every Hyperliquid perp (public info API, no key) = its listing hour -> research_data/hyperliquid_listings/first_funding.json"""
import json
import time
from pathlib import Path
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "research_data/hyperliquid_listings/first_funding.json"; API = "https://api.hyperliquid.xyz/info"


def post(body):
    for i in range(5):
        try:
            r = requests.post(API, json=body, timeout=30)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    return None


def main():
    U = post({"type": "meta"})["universe"]; out = {}
    for u in U:
        h = post({"type": "fundingHistory", "coin": u["name"], "startTime": 0}) or []
        out[u["name"]] = {"first_funding_utc": str(pd.Timestamp(h[0]["time"], unit="ms").floor("s")) if h else None, "delisted": bool(u.get("isDelisted")),
                          "maxLeverage": u.get("maxLeverage")}
        time.sleep(0.3)
    OUT.write_text(json.dumps(out, indent=0)); print(len(out), sum(1 for v in out.values() if v["first_funding_utc"]))


if __name__ == "__main__":
    main()

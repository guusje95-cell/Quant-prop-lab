"""US Treasury auction calendar (TreasuryDirect public API, no account, no key) -> research_data/more2/treasury_auctions.parquet.
Used for the auction-cycle test (Lou, Yan and Zhang 2013): Treasury futures cheapen before auctions and recover after.

    python -m qpl.live.treasury_auctions"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "more2"
HDR = {"User-Agent": "quant-prop-lab research"}
KEEP = ["cusip", "securityType", "securityTerm", "auctionDate", "issueDate", "maturityDate", "offeringAmount", "totalAccepted",
        "bidToCoverRatio", "highYield", "announcementDate"]


def fetch(url, tries=5):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=60) as r:
                return json.loads(r.read())
        except Exception as ex:
            err = ex; time.sleep(2 ** (k + 1))
    raise RuntimeError(f"{url}: {err}")


def main():
    OUT.mkdir(parents=True, exist_ok=True); rows = []
    for y in range(2009, pd.Timestamp.now().year + 1):
        url = ("https://www.treasurydirect.gov/TA_WS/securities/search?format=json&dateFieldName=auctionDate"
               f"&startDate={y}-01-01&endDate={y}-12-31")
        d = fetch(url); rows += d if isinstance(d, list) else d.get("securityList", [])
        print(f"{y}: {len(rows)} auctions so far", flush=True); time.sleep(1)
    df = pd.DataFrame(rows)
    df = df[[c for c in KEEP if c in df.columns]].drop_duplicates()
    df.to_parquet(OUT / "treasury_auctions.parquet", index=False)
    print(f"-> {OUT / 'treasury_auctions.parquet'}: {len(df)} auctions; types {df.securityType.value_counts().to_dict() if 'securityType' in df else ''}")


if __name__ == "__main__":
    main()

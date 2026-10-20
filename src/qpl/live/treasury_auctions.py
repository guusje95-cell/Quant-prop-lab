"""US Treasury auction calendar -> research_data/more2/treasury_auctions.parquet (public, no account, no key).
Primary source: Treasury Fiscal Data API 'auctions_query' (api.fiscaldata.treasury.gov); fallback: TreasuryDirect 'auctioned'.
Used for the auction-cycle test (Lou, Yan and Zhang 2013).

    python -m qpl.live.treasury_auctions"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "more2"
HDR = {"User-Agent": "quant-prop-lab research"}
FISCAL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"


def fetch(url, tries=5):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=60) as r:
                return json.loads(r.read())
        except Exception as ex:
            err = ex; time.sleep(2 ** (k + 1))
    raise RuntimeError(f"{url}: {err}")


def from_fiscal():
    rows, page = [], 1
    while True:
        d = fetch(f"{FISCAL}?filter=auction_date:gte:2009-01-01&sort=auction_date&page[size]=5000&page[number]={page}")
        rows += d.get("data", [])
        total = d.get("meta", {}).get("total-pages", 1)
        print(f"page {page}/{total}: {len(rows)} auctions", flush=True)
        if page >= total:
            break
        page += 1; time.sleep(1)
    df = pd.DataFrame(rows)
    return df.rename(columns={"security_type": "securityType", "security_term": "securityTerm", "auction_date": "auctionDate",
                              "issue_date": "issueDate", "maturity_date": "maturityDate", "offering_amt": "offeringAmount",
                              "bid_to_cover_ratio": "bidToCoverRatio", "high_yield": "highYield", "announcemt_date": "announcementDate"})


def from_treasurydirect():
    rows = []
    for t in ("Bill", "Note", "Bond", "TIPS", "FRN"):
        d = fetch(f"https://www.treasurydirect.gov/TA_WS/securities/auctioned?format=json&type={t}&days=6500")
        rows += d if isinstance(d, list) else []
        print(f"{t}: {len(rows)} so far", flush=True); time.sleep(1)
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        df = from_fiscal()
    except Exception as ex:
        print("Fiscal Data API failed:", ex, "- trying TreasuryDirect", flush=True)
        df = from_treasurydirect()
    keep = [c for c in ("cusip", "securityType", "securityTerm", "auctionDate", "issueDate", "maturityDate", "offeringAmount",
                        "bidToCoverRatio", "highYield", "announcementDate", "reopening") if c in df.columns]
    df = df[keep].astype(str).drop_duplicates()
    df.to_parquet(OUT / "treasury_auctions.parquet", index=False)
    print(f"-> {OUT / 'treasury_auctions.parquet'}: {len(df)} auctions, {df.auctionDate.min()} .. {df.auctionDate.max()}")
    print(df.groupby(["securityType", "securityTerm"]).size().sort_values(ascending=False).head(15).to_string())


if __name__ == "__main__":
    main()

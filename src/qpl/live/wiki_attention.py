"""Gen459 data: daily English-Wikipedia page views (Wikimedia REST API, free, no key) for crypto articles, 2016-..
Run on your own PC (Wikimedia rate-limits the research cloud):   get_wiki_attention.bat
Writes research_data/attention/wiki_pageviews.parquet (columns = article)."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "attention" / "wiki_pageviews.parquet"
UA = {"User-Agent": "quant-prop-lab-research/1.0 (personal research script)"}
ARTICLES = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana_(blockchain_platform)", "XRP": "Ripple_Labs", "BNB": "Binance",
            "DOGE": "Dogecoin", "CRYPTO": "Cryptocurrency", "ADA": "Cardano_(blockchain_platform)", "AVAX": "Avalanche_(blockchain_platform)",
            "LINK": "Chainlink_(blockchain)", "LTC": "Litecoin", "DOT": "Polkadot_(cryptocurrency)", "TRX": "Tron_(cryptocurrency)", "SHIB": "Shiba_Inu_(cryptocurrency)"}


def views(article: str, start="20160101", end=None) -> pd.Series:
    end = end or pd.Timestamp.now("UTC").strftime("%Y%m%d")
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
           f"{urllib.parse.quote(article, safe='')}/daily/{start}/{end}")
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                items = json.loads(r.read().decode())["items"]
            return pd.Series({pd.Timestamp(x["timestamp"][:8]): float(x["views"]) for x in items}, name=article)
        except Exception as e:                                       # noqa: BLE001 - back off politely, then give up on this article
            print(f"  {article}: retry {i + 1} ({e})"); time.sleep(10 * (i + 1))
    return pd.Series(dtype=float, name=article)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True); cols = {}
    for k, a in ARTICLES.items():
        s = views(a); cols[k] = s; print(k, a, len(s)); time.sleep(1.0)
    pd.DataFrame(cols).sort_index().to_parquet(OUT); print("->", OUT)


if __name__ == "__main__":
    main()

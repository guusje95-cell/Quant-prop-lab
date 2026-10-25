"""New free data for research (Gen376): public endpoints only, no account, no key, no payment. Writes research_data/newdata/.

    python -m qpl.live.new_data          (get_new_data.bat)

Sources (each one is optional: a failure is printed and the rest continues):
  - DefiLlama (free public API): total stablecoin supply, DEX volume, perp-DEX volume, DeFi TVL (daily)
  - Blockchain.com charts (free public API): BTC mempool size, transaction fees (USD), miners' revenue (daily)
  - Bybit v5 public market data: BTC/ETH open interest (daily) and account long/short ratio (daily, as far back as Bybit serves)
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "newdata"
UA = {"User-Agent": "Mozilla/5.0 (research; quant-prop-lab)"}


def get(url: str, tries: int = 4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:                                   # noqa: BLE001 - print and retry, then give up on this source
            if i == tries - 1:
                raise
            print(f"  retry {i + 1} ({e})"); time.sleep(2 ** (i + 1))


def save(df: pd.DataFrame, name: str):
    OUT.mkdir(parents=True, exist_ok=True); df.to_parquet(OUT / f"{name}.parquet")
    print(f"  {name}: {len(df)} rows, {df.index.min()} .. {df.index.max()}")


def defillama():
    j = get("https://stablecoins.llama.fi/stablecoincharts/all")
    s = pd.DataFrame({"stablecoin_usd": [float(x["totalCirculatingUSD"].get("peggedUSD", 0.0)) for x in j]},
                     index=pd.to_datetime([int(x["date"]) for x in j], unit="s"))
    save(s, "defillama_stablecoins")
    for kind, name in (("dexs", "defillama_dex_volume"), ("derivatives", "defillama_perpdex_volume")):
        j = get(f"https://api.llama.fi/overview/{kind}?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true&dataType=dailyVolume")
        d = pd.DataFrame(j["totalDataChart"], columns=["t", "volume_usd"]); d.index = pd.to_datetime(d.pop("t"), unit="s")
        save(d.astype(float), name)
    j = get("https://api.llama.fi/v2/historicalChainTvl")
    d = pd.DataFrame(j); d.index = pd.to_datetime(d.pop("date"), unit="s"); save(d.rename(columns={"tvl": "tvl_usd"}).astype(float), "defillama_tvl")


def blockchain_com():
    for chart in ("mempool-size", "transaction-fees-usd", "miners-revenue", "n-transactions"):
        j = get(f"https://api.blockchain.info/charts/{chart}?timespan=all&format=json&sampled=false")
        d = pd.DataFrame(j["values"]); d.index = pd.to_datetime(d.pop("x"), unit="s"); save(d.rename(columns={"y": chart}).astype(float), f"bc_{chart}")


def bybit():
    B = "https://api.bybit.com/v5/market"
    for coin in ("BTC", "ETH"):
        sym = f"{coin}USDT"; rows = []; end = None
        for _ in range(60):                                       # open interest, daily, paged backwards (200 per page)
            u = f"{B}/open-interest?category=linear&symbol={sym}&intervalTime=1d&limit=200" + (f"&endTime={end}" if end else "")
            lst = get(u)["result"]["list"]
            if not lst:
                break
            rows += lst; end = int(lst[-1]["timestamp"]) - 1
            if len(lst) < 200:
                break
            time.sleep(0.2)
        if rows:
            d = pd.DataFrame(rows); d.index = pd.to_datetime(d.pop("timestamp").astype("int64"), unit="ms")
            save(d.astype(float).sort_index()[~d.index.duplicated()], f"bybit_{coin}_oi_1d")
        rows = []; end = None
        for _ in range(60):                                       # account long/short ratio, daily
            u = f"{B}/account-ratio?category=linear&symbol={sym}&period=1d&limit=500" + (f"&endTime={end}" if end else "")
            lst = get(u)["result"]["list"]
            if not lst:
                break
            rows += lst; end = int(lst[-1]["timestamp"]) - 1
            if len(lst) < 500:
                break
            time.sleep(0.2)
        if rows:
            d = pd.DataFrame(rows).drop(columns=["symbol"], errors="ignore"); d.index = pd.to_datetime(d.pop("timestamp").astype("int64"), unit="ms")
            save(d.astype(float).sort_index()[~d.index.duplicated()], f"bybit_{coin}_account_ratio_1d")


def main():
    for name, fn in (("DefiLlama", defillama), ("Blockchain.com", blockchain_com), ("Bybit", bybit)):
        print(name)
        try:
            fn()
        except Exception as e:                                   # noqa: BLE001
            print(f"  FAILED: {e} (paste this line to Claude; the other sources still run)")
    print(f"done -> {OUT}")


if __name__ == "__main__":
    main()

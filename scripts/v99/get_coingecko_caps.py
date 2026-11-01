"""Daily market cap and 24h volume (last 365 days, CoinGecko free public API) of every coin the v9.8 event short held in 2025-10..2026-09,
for the HyroTrader low-cap classification (market cap < $100M or 24h volume $0.5M-$5M). Symbol -> id: among CoinGecko ids with that
symbol, the one with the largest current market cap. -> research_data/coingecko_lowcap/<COIN>.parquet + mapping.json"""
import json
import sys
import time
from pathlib import Path
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]; sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
OUT = ROOT / "research_data/coingecko_lowcap"; API = "https://api.coingecko.com/api/v3"


def get(url, params=None):
    for i in range(6):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        time.sleep(20 * (i + 1) if r.status_code == 429 else 3)
    return None


def main():
    import event_live as EL
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); _, pos, _ = EL.pnl(V.index)
    p = pos.loc["2025-10-01":"2026-09-30"]; coins = sorted({c[4:] if c.startswith("spo_") else c for c in p.columns[(p != 0).any()]})
    L = get(f"{API}/coins/list"); by = {}
    for x in L:
        by.setdefault(x["symbol"].upper(), []).append(x["id"])
    syms = {c: (c[4:] if c.startswith("1000") and c[4:] else c) for c in coins}
    allids = sorted({i for c in coins for i in by.get(syms[c], [])}); mcap = {}
    for k in range(0, len(allids), 200):                                   # batched: 200 ids per call
        m = get(f"{API}/coins/markets", {"vs_currency": "usd", "ids": ",".join(allids[k:k + 200]), "per_page": 250}) or []; time.sleep(6)
        mcap.update({x["id"]: x.get("market_cap") or 0 for x in m})
    mapping = {}
    for c in coins:
        ids = by.get(syms[c], [])
        mapping[c] = max(ids, key=lambda i: mcap.get(i, 0)) if ids else None
        print("map", c, mapping[c], flush=True)
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "mapping.json").write_text(json.dumps(mapping, indent=1))
    for c, cid in mapping.items():
        if not cid or (OUT / f"{c}.parquet").exists():
            continue
        j = get(f"{API}/coins/{cid}/market_chart", {"vs_currency": "usd", "days": 365, "interval": "daily"}); time.sleep(7)
        if not j:
            continue
        d = pd.DataFrame({"mcap": {pd.Timestamp(t, unit="ms").normalize(): v for t, v in j.get("market_caps", [])},
                          "volume": {pd.Timestamp(t, unit="ms").normalize(): v for t, v in j.get("total_volumes", [])}})
        d.to_parquet(OUT / f"{c}.parquet"); print(c, cid, len(d), flush=True)
    print("done", sum(1 for v in mapping.values() if v), "of", len(mapping))


if __name__ == "__main__":
    main()

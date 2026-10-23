"""Hyperliquid check for v8.6 at Propr (Propr's accounts price and fill on Hyperliquid perps). Public market data only: no
wallet, no account, no API key. Run on your own PC (Hyperliquid is not reachable from the research cloud):

    python -m qpl.live.hyperliquid_check

For every coin of the v8.6 universe:
  1. listing: is a native Hyperliquid perp trading (names like kPEPE / kSHIB matched), its max leverage, size decimals, delisted flag
  2. funding history since 2023-05 (hourly settlements; what a Hyperliquid position pays)
  3. spread: 10 order-book snapshots 20 s apart -> median bid-ask spread (bp) and the dollar depth at the best bid / ask
Output: research_data/hyperliquid/instruments.csv, spreads.csv, funding/<COIN>.parquet. Resumable. About 15-30 minutes."""
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from qpl.live.bybit_check import norm, universe

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "hyperliquid"
API = "https://api.hyperliquid.xyz/info"


def post(body):
    for k in range(6):
        try:
            req = urllib.request.Request(API, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "qpl"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as ex:
            err = ex; time.sleep(2 ** (k + 1))
    raise RuntimeError(f"{body}: {err}")


def funding(coin, name):
    f = OUT / "funding" / f"{coin}.parquet"; f.parent.mkdir(parents=True, exist_ok=True)
    old = pd.read_parquet(f) if f.exists() else None
    start = int(old.index.max().timestamp() * 1000) + 1 if old is not None else int(pd.Timestamp("2023-05-01", tz="UTC").timestamp() * 1000)
    rows = []
    while start < time.time() * 1000 - 3_600_000:
        lst = post({"type": "fundingHistory", "coin": name, "startTime": start})
        if not lst:
            break
        rows += lst; start = max(int(x["time"]) for x in lst) + 1; time.sleep(0.25)
        if len(lst) < 500:
            break
    if rows:
        d = pd.DataFrame(rows); d.index = pd.to_datetime(d["time"].astype("int64"), unit="ms"); d.index.name = "time"
        d = d[["fundingRate"]].astype(float).rename(columns={"fundingRate": "funding_rate"})
        if old is not None:
            d = pd.concat([old, d])
        d = d[~d.index.duplicated(keep="last")].sort_index(); d.to_parquet(f)
        return len(d), d.index.min()
    return (len(old), old.index.min()) if old is not None else (0, None)


def spread(name, n=10, gap=20):
    sp, depth = [], []
    for k in range(n):
        try:
            b, a = post({"type": "l2Book", "coin": name})["levels"]
            bid, ask = float(b[0]["px"]), float(a[0]["px"]); mid = (bid + ask) / 2
            sp.append((ask - bid) / mid * 1e4); depth.append(min(float(b[0]["sz"]) * bid, float(a[0]["sz"]) * ask))
        except Exception:
            pass
        if k < n - 1:
            time.sleep(gap)
    s = pd.Series(sp, dtype=float); d = pd.Series(depth, dtype=float)
    return (round(float(s.median()), 2) if len(s) else None, round(float(d.median())) if len(d) else None, len(s))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = post({"type": "meta"})["universe"]; by = {}
    for u in meta:
        by.setdefault(norm(u["name"].lstrip("k") if u["name"].startswith("k") and u["name"][1:].isupper() else u["name"]), []).append(u)
    rows = []
    for c in universe():
        cand = [u for u in by.get(norm(c), []) if not u.get("isDelisted")]
        u = cand[0] if cand else None
        rows.append({"coin": c, "listed": u is not None, "name": u["name"] if u else "", "max_leverage": u.get("maxLeverage", "") if u else "",
                     "sz_decimals": u.get("szDecimals", "") if u else "", "only_isolated": u.get("onlyIsolated", False) if u else ""})
    I = pd.DataFrame(rows); I.to_csv(OUT / "instruments.csv", index=False)
    print(f"{int(I.listed.sum())} of {len(I)} coins have a Hyperliquid perp; missing: {list(I.loc[~I.listed, 'coin'])}", flush=True)
    for _, r in I[I.listed].iterrows():
        try:
            n, first = funding(r.coin, r["name"]); print(f"  funding {r['name']}: {n} rows from {first}", flush=True)
        except Exception as e:
            print(f"  funding {r['name']}: {e.__class__.__name__} (run again later)", flush=True)
    print("spreads: 10 snapshots per coin, 20 s apart (batches of 10 coins) ...", flush=True)
    names = list(I.loc[I.listed, "name"])
    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(spread, names))
    S = pd.DataFrame({"name": names, "spread_bp_median": [x[0] for x in res], "top_depth_usd_median": [x[1] for x in res],
                      "samples": [x[2] for x in res], "measured_utc": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M")})
    S.to_csv(OUT / "spreads.csv", index=False)
    print(S.sort_values("spread_bp_median").to_string(index=False), flush=True)
    print("done -> research_data/hyperliquid (git add research_data/hyperliquid, commit, push)", flush=True)


if __name__ == "__main__":
    main()

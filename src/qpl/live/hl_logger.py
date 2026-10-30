"""Hyperliquid market snapshot logger (forward data collection for crypto research: open interest, funding, premium, volume of ~230 perps).
Hyperliquid's public API has no open-interest history, so the history has to be recorded going forward. Public data only: no key, no orders.
The hub runs it every hour (job 'hl_snapshot'); one row per coin per snapshot is appended to research_data/hyperliquid_live/<YYYY-MM>.csv."""
from __future__ import annotations

import csv
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "hyperliquid_live"
FIELDS = ["ts_utc", "coin", "markPx", "oraclePx", "midPx", "funding", "premium", "openInterest", "dayNtlVlm", "prevDayPx", "maxLeverage"]


def snapshot() -> int:
    r = requests.post("https://api.hyperliquid.xyz/info", json={"type": "metaAndAssetCtxs"}, timeout=30); r.raise_for_status()
    meta, ctx = r.json()
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    OUT.mkdir(parents=True, exist_ok=True); f = OUT / f"{ts[:7]}.csv"; new = not f.exists()
    with open(f, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        if new:
            w.writeheader()
        n = 0
        for u, c in zip(meta["universe"], ctx):
            if u.get("isDelisted"):
                continue
            w.writerow({"ts_utc": ts, "coin": u["name"], "maxLeverage": u.get("maxLeverage"), **{k: c.get(k) for k in FIELDS if k in c}}); n += 1
    return n


if __name__ == "__main__":
    print(snapshot(), "coins logged")

"""New-information collectors (task D1, 2026-11-03): public announcement / listing data that is NOT available historically, collected
forward so that pre-registered event tests become possible in a few months. Public APIs only, no keys, no orders.

  okx        OKX support announcements (new listings, delistings)          -> research_data/collect/okx_announcements.json
  bitget     Bitget announcements (coin listings: spot / futures)         -> research_data/collect/bitget_announcements.json
  bybit      Bybit announcements (new crypto, delistings; may be geo-blocked)-> research_data/collect/bybit_announcements.json
  hl         Hyperliquid perp universe: first-seen hour of every coin, and hourly candles of coins listed in the last 30 days
             -> research_data/collect/hl_first_seen.json, research_data/collect/hl_new/<COIN>_1h.parquet

Each source is independent (one failing never blocks the others). Records are merged by id, never deleted.

    python -m qpl.live.listing_collectors        # one pass (the hub job 'collect_listings' runs it every hour)"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data/collect"
UA = {"User-Agent": "qpl-research-collector"}


def _merge(f: Path, rows: list[dict], key: str) -> int:
    old = json.loads(f.read_text()) if f.exists() else {}
    n = 0
    for r in rows:
        k = str(r.get(key))
        if k and k not in old:
            old[k] = dict(r, first_seen_utc=str(pd.Timestamp.now(tz="UTC").tz_localize(None).floor("s"))); n += 1
    f.parent.mkdir(parents=True, exist_ok=True); tmp = f.with_suffix(".tmp"); tmp.write_text(json.dumps(old, indent=0)); tmp.replace(f)
    return n


def okx() -> int:
    rows = []
    for t in ("announcements-new-listings", "announcements-delistings"):
        for page in range(1, 4):
            j = requests.get("https://www.okx.com/api/v5/support/announcements", params={"annType": t, "page": page}, headers=UA, timeout=20).json()
            det = [x for d in (j.get("data") or []) for x in d.get("details", [])]
            rows += [dict(x, id=f"{x.get('pTime')}|{x.get('title')}") for x in det]
            if not det:
                break
            time.sleep(0.3)
    return _merge(OUT / "okx_announcements.json", rows, "id")


def bitget() -> int:
    rows = []
    for t in ("coin_listings", "symbol_delisting"):
        j = requests.get("https://api.bitget.com/api/v2/public/annoucements", params={"language": "en_US", "annType": t, "limit": 10}, headers=UA, timeout=20).json()
        rows += j.get("data") or []
    return _merge(OUT / "bitget_announcements.json", rows, "annId")


def bybit() -> int:
    rows = []
    for t in ("new_crypto", "delistings"):
        j = requests.get("https://api.bybit.com/v5/announcements/index", params={"locale": "en-US", "type": t, "limit": 20}, headers=UA, timeout=20).json()
        rows += [dict(x, id=f"{x.get('dateTimestamp')}|{x.get('title')}") for x in ((j.get("result") or {}).get("list") or [])]
    return _merge(OUT / "bybit_announcements.json", rows, "id")


def hl() -> int:
    api = "https://api.hyperliquid.xyz/info"
    meta = requests.post(api, json={"type": "meta"}, headers=UA, timeout=30).json()
    now = pd.Timestamp.now(tz="UTC").tz_localize(None).floor("h")
    f = OUT / "hl_first_seen.json"; seen = json.loads(f.read_text()) if f.exists() else {}
    first_run = not seen; new = 0
    for u in meta.get("universe", []):
        if u["name"] not in seen:
            seen[u["name"]] = {"first_seen_utc": None if first_run else str(now), "maxLeverage": u.get("maxLeverage")}; new += 0 if first_run else 1
    f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(seen, indent=0))
    d = OUT / "hl_new"; d.mkdir(parents=True, exist_ok=True)
    for coin, v in seen.items():                                      # hourly candles of coins first seen in the last 30 days
        if v["first_seen_utc"] and now - pd.Timestamp(v["first_seen_utc"]) <= pd.Timedelta(days=30):
            c = requests.post(api, json={"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h",
                                                                          "startTime": int((pd.Timestamp(v["first_seen_utc"]) - pd.Timedelta(days=1)).value // 1e6)}},
                              headers=UA, timeout=30).json() or []
            if c:
                df = pd.DataFrame([{"t": pd.Timestamp(int(k["t"]), unit="ms"), "o": float(k["o"]), "h": float(k["h"]), "l": float(k["l"]), "c": float(k["c"]), "v": float(k["v"])} for k in c]).set_index("t")
                df.to_parquet(d / f"{coin}_1h.parquet")
            time.sleep(0.3)
    return new


def step(log=print) -> dict:
    res = {}
    for name, fn in (("okx", okx), ("bitget", bitget), ("bybit", bybit), ("hyperliquid", hl)):
        try:
            res[name] = fn()
        except Exception as e:                                          # noqa: BLE001 - one source must not block the others
            res[name] = f"failed: {str(e)[:120]}"
    return res


if __name__ == "__main__":
    print(json.dumps(step(), indent=1))

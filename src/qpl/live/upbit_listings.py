"""Upbit KRW listing detector (public API, no key, never trades): the first time a KRW market appears in /v1/market/all, its first
hourly candle is looked up and stored in research_data/upbit_listings/first_trade.json. On the first run every existing market is
recorded as 'seed' (no event), so only markets listed AFTER the detector started become events (v9.9 R22 / R30 A rules)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
FILE = ROOT / "research_data/upbit_listings/first_trade.json"
API = "https://api.upbit.com/v1"


def _get(path, params=None):
    r = requests.get(API + path, params=params, timeout=30)
    if r.status_code in (403, 451):
        raise RuntimeError(f"Upbit refused the request from this location ({r.status_code}); not bypassing it")
    r.raise_for_status(); return r.json()


def first_hour(market: str) -> str | None:
    """earliest hourly candle of a NEW market (its whole history fits in 200 hourly candles for a few days)"""
    c = _get("/candles/minutes/60", {"market": market, "count": 200})
    return min(x["candle_date_time_utc"] for x in c).replace("T", " ") if c else None


def detector(log=print) -> int:
    M = [m["market"] for m in _get("/market/all") if m["market"].startswith("KRW-")]
    D = json.loads(FILE.read_text()) if FILE.exists() else {}; seeding = not D; now = str(pd.Timestamp.now(tz="UTC").tz_localize(None).floor("s")); new = 0
    for m in M:
        if m in D:
            continue
        if seeding:
            D[m] = {"base": m[4:], "seed": True, "first_trade_utc": None, "detected_utc": now}; continue
        D[m] = {"base": m[4:], "first_trade_utc": first_hour(m), "detected_utc": now}; new += 1
        log(f"new Upbit market {m}: first hour {D[m]['first_trade_utc']}")
    FILE.parent.mkdir(parents=True, exist_ok=True); tmp = FILE.with_suffix(".tmp"); tmp.write_text(json.dumps(D, indent=0), encoding="utf-8"); tmp.replace(FILE)
    return new


def events(start: pd.Timestamp) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    D = json.loads(FILE.read_text()) if FILE.exists() else {}
    return {v["base"]: (pd.Timestamp(v["first_trade_utc"]), pd.Timestamp(v["detected_utc"])) for v in D.values()
            if not v.get("seed") and v.get("first_trade_utc") and pd.Timestamp(v["first_trade_utc"]) >= start}

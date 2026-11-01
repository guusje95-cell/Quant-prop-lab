"""Coinbase sell-the-news short (v9.9 R16 / R16b candidate): live listing detector + frozen-ledger PAPER sleeve. Public data only,
no keys, never places an order.

1. detector(): polls the public Coinbase Exchange product list; a new USD / USDT / USDC product gets its first trading hour from the
   public candles (same method as scripts/v99/get_coinbase_listings.py) and is added to research_data/coinbase_listings/first_trade.json.
2. step(): for every non-stable Coinbase first listing at or after START whose coin has a Binance USDT-M perp, the paper sleeve is short
   SIZE (5% of equity) from the close of the hour after the first Coinbase hour (= R16b entry, T + 2 h) for 7 days, out early when an
   hourly close is >= 30% above the entry; 10 bp per side; Binance funding charged. Each COMPLETED hour is appended once to
   paper_trading/cbshort/ledger_hourly.csv (frozen ledger, same format as the v9.8 paper trader; 'hour' = bar open, 'port' = sleeve
   return as a fraction of equity). The hub ingests it as paper:cbshort and the shadow 'v98:plus_coinbase_short' adds it to the v9.8
   paper book through the listing-short weight. v9.8 itself is unchanged.

    python -m qpl.live.coinbase_short            # one detector + paper step (the hub job 'cbshort_paper' runs it every hour)"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
FIRST = ROOT / "research_data/coinbase_listings/first_trade.json"
OUT = ROOT / "paper_trading/cbshort"
CB = "https://api.exchange.coinbase.com"
FAPI = "https://fapi.binance.com"
START = pd.Timestamp("2026-11-01 00:00")
SIZE, HOLD_H, STOP, COST = 0.05, 24 * 7, 0.30, 1e-3
EXCL = {"USDT", "USDC", "DAI", "PYUSD", "EURC", "WBTC", "CBETH", "GUSD", "PAX", "USD", "EUR", "GBP"}
COL = "coinbase short"


def _get(url, params=None, tries=5):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=30)
        except requests.RequestException:
            time.sleep(2 ** i); continue
        if r.status_code == 429:
            time.sleep(2 ** i); continue
        if r.status_code in (403, 451):
            raise RuntimeError(f"{url}: refused from this location ({r.status_code}); not bypassing it")
        return r.json() if r.status_code == 200 else None
    return None


def first_trade(pid: str, since: pd.Timestamp = pd.Timestamp("2019-01-01")) -> str | None:
    t = since.tz_localize("UTC") if since.tzinfo is None else since; now = pd.Timestamp.now(tz="UTC")
    while t < now:
        e = min(t + pd.Timedelta(days=299), now); c = _get(f"{CB}/products/{pid}/candles", {"start": t.isoformat(), "end": e.isoformat(), "granularity": 86400})
        time.sleep(0.15)
        if c:
            d0 = pd.Timestamp(min(x[0] for x in c), unit="s", tz="UTC")
            h = _get(f"{CB}/products/{pid}/candles", {"start": d0.isoformat(), "end": (d0 + pd.Timedelta(hours=24)).isoformat(), "granularity": 3600})
            return str(pd.Timestamp(min(x[0] for x in h), unit="s") if h else d0.tz_localize(None))
        t = e
    return None


def detector(log=print) -> int:
    P = _get(f"{CB}/products") or []
    D = json.loads(FIRST.read_text()) if FIRST.exists() else {}; new = 0
    for p in P:
        if p.get("quote_currency") not in ("USD", "USDT", "USDC") or p["id"] in D:
            continue
        ft = first_trade(p["id"], since=pd.Timestamp.now().normalize() - pd.Timedelta(days=30))   # a new product: only the last 30 days
        D[p["id"]] = {"base": p["base_currency"], "quote": p["quote_currency"], "status": p.get("status"), "first_trade_utc": ft,
                      "detected_utc": str(pd.Timestamp.now(tz="UTC").tz_localize(None).floor("s"))}
        new += 1; log(f"new Coinbase product {p['id']}: first trade {ft}")
    if new:
        FIRST.parent.mkdir(parents=True, exist_ok=True); tmp = FIRST.with_suffix(".tmp"); tmp.write_text(json.dumps(D, indent=0), encoding="utf-8"); tmp.replace(FIRST)
    return new


def events(D: dict | None = None) -> dict[str, tuple[pd.Timestamp, pd.Timestamp | None]]:
    """base coin -> (first Coinbase trading hour, time our detector saw the product or None for products already in the research file)"""
    D = D if D is not None else (json.loads(FIRST.read_text()) if FIRST.exists() else {})
    first = {}
    for p in D.values():
        if p.get("first_trade_utc") and p["base"] not in EXCL:
            t = pd.Timestamp(p["first_trade_utc"]); d = pd.Timestamp(p["detected_utc"]) if p.get("detected_utc") else None
            if p["base"] not in first or t < first[p["base"]][0]:
                first[p["base"]] = (t, d)
    return {c: v for c, v in first.items() if v[0] >= START}


def klines(coin: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series | None:
    """hourly closes indexed by bar OPEN time (completed bars only), or None if Binance has no such USDT perp"""
    rows = _get(f"{FAPI}/fapi/v1/klines", {"symbol": f"{coin}USDT", "interval": "1h", "startTime": int(start.value // 1e6), "endTime": int(end.value // 1e6), "limit": 1500})
    if not rows or isinstance(rows, dict):
        return None
    s = pd.Series([float(r[4]) for r in rows], index=pd.to_datetime([r[0] for r in rows], unit="ms"))
    return s[s.index + pd.Timedelta(hours=1) <= pd.Timestamp.now(tz="UTC").tz_localize(None)]


def funding(coin: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    rows = _get(f"{FAPI}/fapi/v1/fundingRate", {"symbol": f"{coin}USDT", "startTime": int(start.value // 1e6), "endTime": int(end.value // 1e6), "limit": 1000}) or []
    return pd.Series([float(r["fundingRate"]) for r in rows], index=pd.to_datetime([r["fundingTime"] for r in rows], unit="ms").floor("h")) if rows else pd.Series(dtype=float)


def trade_pnl(cl: pd.Series, fu: pd.Series, T: pd.Timestamp, detected: pd.Timestamp | None = None) -> pd.Series:
    """hourly P&L (fraction of equity) labelled by bar open, from the R16b rules; cl = closes by bar open time. If our detector saw the
    listing later than T + 1 h, the entry is the close of the bar in which it was detected (no P&L before we could have known)."""
    entry_bar = T.floor("h") + pd.Timedelta(hours=1)                    # close of this bar (at T + 2 h) is the entry
    if detected is not None:
        entry_bar = max(entry_bar, detected.floor("h"))
    if entry_bar not in cl.index:
        return pd.Series(dtype=float)
    p0 = cl.loc[entry_bar]; path = cl.loc[entry_bar:entry_bar + pd.Timedelta(hours=HOLD_H)]
    hit = path.index[(path >= p0 * (1 + STOP)).to_numpy()]; last = hit[0] if len(hit) else path.index[-1]
    path = path.loc[:last]; r = path.pct_change().iloc[1:]
    pnl = -SIZE * r
    settle = fu.reindex(r.index + pd.Timedelta(hours=1)).fillna(0.0).to_numpy()       # a settlement at the end of bar h is paid in bar h
    pnl = pnl + SIZE * settle
    if len(pnl):
        pnl.iloc[0] -= SIZE * COST                                       # entry (charged in the first held bar)
        done = len(hit) > 0 or last >= entry_bar + pd.Timedelta(hours=HOLD_H)
        if done:
            pnl.iloc[-1] -= SIZE * COST
    return pnl


def step(log=print) -> dict:
    try:
        new = detector(log)
    except Exception as e:                                               # noqa: BLE001 - the ledger must advance even if Coinbase is down
        new = f"detector failed: {e}"
    now = pd.Timestamp.now(tz="UTC").tz_localize(None); last_done = now.floor("h") - pd.Timedelta(hours=1)
    E = events(); total = pd.Series(0.0, index=pd.date_range(START, last_done, freq="h")); traded = {}
    for coin, (T, det) in E.items():
        cl = klines(coin, T.floor("h") - pd.Timedelta(hours=3), T + pd.Timedelta(hours=HOLD_H + 4))
        if cl is None or not ((cl.index >= T.floor("h") - pd.Timedelta(hours=3)) & (cl.index <= T.floor("h"))).any():
            traded[coin] = "no Binance perp at the listing"; continue
        p = trade_pnl(cl, funding(coin, T - pd.Timedelta(days=1), T + pd.Timedelta(hours=HOLD_H + 4)), T, det)
        total = total.add(p.reindex(total.index).fillna(0.0), fill_value=0.0); traded[coin] = f"{len(p)} hours"
    OUT.mkdir(parents=True, exist_ok=True); f = OUT / "ledger_hourly.csv"
    L = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["hour", COL, "port", "computed_at", "lag_h", "late"])
    have = set(L["hour"].astype(str)); rows = []
    for h, v in total.items():
        k = str(h)
        if k in have:
            continue                                                     # frozen: an hour is written once
        lag = (now - (h + pd.Timedelta(hours=1))).total_seconds() / 3600
        rows.append({"hour": k, COL: float(v), "port": float(v), "computed_at": str(now), "lag_h": round(lag, 3), "late": lag > 30})
    if rows:
        L = pd.concat([L, pd.DataFrame(rows)], ignore_index=True); tmp = f.with_suffix(".tmp"); L.to_csv(tmp, index=False); tmp.replace(f)
    (OUT / "events.json").write_text(json.dumps({c: {"first_coinbase_hour": str(E[c][0]), "detected": str(E[c][1]), "status": s} for c, s in traded.items()}, indent=1), encoding="utf-8")
    return {"new_products": new, "events_since_start": len(E), "hours_written": len(rows), "events": traded}


if __name__ == "__main__":
    print(json.dumps(step(), indent=1, default=str))

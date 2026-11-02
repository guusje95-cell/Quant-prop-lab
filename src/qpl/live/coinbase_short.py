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
3. The same rules on Coinbase + new Upbit KRW listings (qpl.live.upbit_listings; Upbit coins need a >= 7-day-old Binance perp, R22)
   -> paper_trading/venueshort (paper:venueshort; R30 A).

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


def trade_pnl(cl: pd.Series, fu: pd.Series, T: pd.Timestamp, detected: pd.Timestamp | None = None, hold_h: int = HOLD_H) -> pd.Series:
    """hourly P&L (fraction of equity) labelled by bar open, from the R16b rules; cl = closes by bar open time. If our detector saw the
    listing later than T + 1 h, the entry is the close of the bar in which it was detected (no P&L before we could have known)."""
    entry_bar = T.floor("h") + pd.Timedelta(hours=1)                    # close of this bar (at T + 2 h) is the entry
    if detected is not None:
        entry_bar = max(entry_bar, detected.floor("h"))
    if entry_bar not in cl.index:
        return pd.Series(dtype=float)
    p0 = cl.loc[entry_bar]; path = cl.loc[entry_bar:entry_bar + pd.Timedelta(hours=hold_h)]
    hit = path.index[(path >= p0 * (1 + STOP)).to_numpy()]; last = hit[0] if len(hit) else path.index[-1]
    path = path.loc[:last]; r = path.pct_change().iloc[1:]
    pnl = -SIZE * r
    settle = fu.reindex(r.index + pd.Timedelta(hours=1)).fillna(0.0).to_numpy()       # a settlement at the end of bar h is paid in bar h
    pnl = pnl + SIZE * settle
    if len(pnl):
        pnl.iloc[0] -= SIZE * COST                                       # entry (charged in the first held bar)
        done = len(hit) > 0 or last >= entry_bar + pd.Timedelta(hours=hold_h)
        if done:
            pnl.iloc[-1] -= SIZE * COST
    return pnl


def _run(E: list[tuple[str, pd.Timestamp, pd.Timestamp | None, str]], out: Path, col: str, min_perp_days: dict, now: pd.Timestamp, hold_h: dict | None = None) -> dict:
    """E = [(coin, first venue hour, detected time or None, venue)]; a coin is not shorted again within 7 days (as in R18 / R22 / R30)"""
    last_done = now.floor("h") - pd.Timedelta(hours=1); total = pd.Series(0.0, index=pd.date_range(START, last_done, freq="h")); traded = {}; last = {}
    for coin, T, det, venue in sorted(E, key=lambda e: e[1]):
        key = f"{coin} ({venue})"
        if coin in last and T - last[coin] < pd.Timedelta(days=7):
            traded[key] = "skipped: same coin shorted within 7 days"; continue
        back = pd.Timedelta(days=min_perp_days.get(venue, 0)) + pd.Timedelta(hours=3)
        cl = klines(coin, T.floor("h") - back, T + pd.Timedelta(hours=HOLD_H + 4))
        if cl is None or not ((cl.index >= T.floor("h") - pd.Timedelta(hours=3)) & (cl.index <= T.floor("h"))).any():
            traded[key] = "no Binance perp at the listing"; continue
        if min_perp_days.get(venue) and cl.index.min() > T - pd.Timedelta(days=min_perp_days[venue]):
            traded[key] = f"Binance perp younger than {min_perp_days[venue]} days"; continue
        hh = (hold_h or {}).get(venue, HOLD_H)
        if hh > HOLD_H:
            cl = klines(coin, T.floor("h") - back, T + pd.Timedelta(hours=hh + 4))
        p = trade_pnl(cl, funding(coin, T - pd.Timedelta(days=1), T + pd.Timedelta(hours=hh + 4)), T, det, hh)
        total = total.add(p.reindex(total.index).fillna(0.0), fill_value=0.0); traded[key] = f"{len(p)} hours"; last[coin] = T
    out.mkdir(parents=True, exist_ok=True); f = out / "ledger_hourly.csv"
    L = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["hour", col, "port", "computed_at", "lag_h", "late"])
    have = set(L["hour"].astype(str)); rows = []
    for h, v in total.items():
        if str(h) in have:
            continue                                                     # frozen: an hour is written once
        lag = (now - (h + pd.Timedelta(hours=1))).total_seconds() / 3600
        rows.append({"hour": str(h), col: float(v), "port": float(v), "computed_at": str(now), "lag_h": round(lag, 3), "late": lag > 30})
    if rows:
        L = pd.concat([L, pd.DataFrame(rows)], ignore_index=True); tmp = f.with_suffix(".tmp"); L.to_csv(tmp, index=False); tmp.replace(f)
    (out / "events.json").write_text(json.dumps({k: {"status": s} for k, s in traded.items()}, indent=1), encoding="utf-8")
    return {"events": len(E), "hours_written": len(rows), "status": traded}


def step(log=print) -> dict:
    """Coinbase only (paper:cbshort; R16 / R30 B) and Coinbase + Upbit (paper:venueshort; R30 A)."""
    from qpl.live import upbit_listings as UP
    res = {}
    for name, fn in (("coinbase", detector), ("upbit", UP.detector), ("upbit warning changes", UP.log_warnings)):
        try:
            res[f"new {name} listings"] = fn(log)
        except Exception as e:                                           # noqa: BLE001 - the ledgers must advance even if a venue is down
            res[f"new {name} listings"] = f"detector failed: {e}"
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    CE = [(c, T, d, "coinbase") for c, (T, d) in events().items()]
    UE = [(c, T, d, "upbit") for c, (T, d) in UP.events(START).items()]
    res["coinbase"] = _run(CE, OUT, COL, {}, now)
    res["coinbase + upbit"] = _run(CE + UE, ROOT / "paper_trading/venueshort", "venue listing short", {"upbit": 7}, now)
    FE = [(c, T, None, "binance futures delisting") for c, T in futures_delistings()]
    res["binance futures delisting"] = _run(FE, ROOT / "paper_trading/fdshort", "futures-delisting short", {}, now, {"binance futures delisting": 14 * 24})
    try:
        from qpl.live import binance_announcements as BA
        res["new binance 'add' announcements"] = BA.update(ROOT / "paper_trading/eventdata", catalog=48, log=lambda *a: None)
    except Exception as e:                                               # noqa: BLE001
        res["new binance 'add' announcements"] = f"failed: {e}"
    AE = [(c, T, None, "binance add") for c, T in binance_adds()]
    res["binance add"] = _run(AE, ROOT / "paper_trading/addshort", "binance add short", {"binance add": 7}, now)
    return res


def binance_adds() -> list[tuple[str, pd.Timestamp]]:
    """'Binance Will Add <Name> (<TICKER>) on ... Margin' announcements (catalog 48, new listings) at or after START (R34); the coin's
    Binance perp must be >= 7 days old (checked in _run). T = release.ceil('h') - 1 h, so the entry is the first whole hour + 1 h."""
    import re
    arts = {}
    for f in (ROOT / "research_data/binance_announcements/catalog_48.json", ROOT / "paper_trading/eventdata/announcements/catalog_48.json"):
        try:
            arts.update({a["id"]: a for a in json.loads(f.read_text(encoding="utf-8"))["articles"]})
        except (OSError, ValueError, KeyError):
            continue
    out = []
    for a in arts.values():
        t = pd.to_datetime(a["releaseDate"], unit="ms")
        if t < START or not re.match(r"Binance Will Add .+ on .*Margin", a["title"]):
            continue
        out += [(tk, t.ceil("h") - pd.Timedelta(hours=1)) for tk in re.findall(r"\(([A-Z0-9]{2,15})\)", a["title"])]
    return out


def futures_delistings() -> list[tuple[str, pd.Timestamp]]:
    """'Binance Futures Will Delist <SYM>USDT ... Perpetual' announcements (not 'Multiple') at or after START, from the research archive and
    the live catalog the v9.8 paper trader downloads (paper_trading/v98/data/announcements/catalog_161.json). The entry rule of R32 B
    (first whole hour after the release + 1 h) is expressed as T = release.ceil('h') - 1 h for trade_pnl (entry = close of bar T + 1 h)."""
    import re
    arts = {}
    for f in (ROOT / "research_data/binance_announcements/catalog_161.json", ROOT / "paper_trading/v98/data/announcements/catalog_161.json"):
        try:
            arts.update({a["id"]: a for a in json.loads(f.read_text(encoding="utf-8"))["articles"]})
        except (OSError, ValueError, KeyError):
            continue
    out = []
    for a in arts.values():
        t = pd.to_datetime(a["releaseDate"], unit="ms")
        if t < START or not a["title"].startswith("Binance Futures Will Delist") or "Multiple" in a["title"]:
            continue
        out += [(x[:-4], t.ceil("h") - pd.Timedelta(hours=1)) for x in re.findall(r"([A-Z0-9]{2,15}USDT)", a["title"])]
    return out


if __name__ == "__main__":
    print(json.dumps(step(), indent=1, default=str))

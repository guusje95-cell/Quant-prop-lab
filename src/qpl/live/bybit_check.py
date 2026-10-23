"""Bybit reality check for v8.6 (HyroTrader trades Bybit USDT perps; our research data is Binance). Public market data only:
no account, no API key. Run on your own PC (Bybit is not reachable from the research cloud):

    python -m qpl.live.bybit_check

For every coin of the v8.6 universe (20 pack coins + the extra coins in research_data/binance_extra):
  1. listing: is a USDT perpetual trading on Bybit, its symbol (e.g. SHIB1000USDT), min order qty, qty step, tick size, max leverage
  2. funding history since 2020 (every settlement; Bybit funding differs from Binance funding and is what the account pays)
  3. spread: 10 order-book snapshots 20 s apart -> median bid-ask spread (bp) and the dollar depth at the best bid / ask
Output: research_data/bybit/instruments.csv, spreads.csv, funding/<SYMBOL>.parquet. Resumable (finished funding files are
extended, not re-downloaded). About 15-30 minutes."""
import time
from pathlib import Path

import pandas as pd

from qpl.live.more_data import get

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "bybit"
API = "https://api.bybit.com"
PACK = ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "AVAX", "DOT", "LINK", "LTC", "BCH", "TRX", "ETC", "XLM", "ATOM", "NEAR", "FIL", "UNI", "AAVE"]


def universe():
    extra = sorted(p.stem.replace("USDT_1h", "") for p in (ROOT / "research_data/binance_extra").glob("*USDT_1h.parquet"))
    return PACK + [c for c in extra if c not in PACK]


def instruments():
    rows, cursor = [], ""
    while True:
        js = get(f"{API}/v5/market/instruments-info?category=linear&limit=1000" + (f"&cursor={cursor}" if cursor else ""))
        res = js["result"]; rows += res["list"]; cursor = res.get("nextPageCursor") or ""
        if not cursor:
            break
    return [r for r in rows if r.get("quoteCoin") == "USDT" and r.get("contractType") == "LinearPerpetual"]


def norm(base):
    """'1000PEPE' / 'SHIB1000' / '10000SATS' -> core name, so Binance and Bybit names can be matched."""
    b = base.upper()
    for p in ("1000000", "10000", "1000"):
        b = b.replace(p, "")
    return b


def funding(symbol):
    f = OUT / "funding" / f"{symbol}.parquet"; f.parent.mkdir(parents=True, exist_ok=True)
    old = pd.read_parquet(f) if f.exists() else None
    start = int(old.index.max().timestamp() * 1000) + 1 if old is not None else int(pd.Timestamp("2020-01-01", tz="UTC").timestamp() * 1000)
    end = int(time.time() * 1000); rows = []
    while end > start:
        js = get(f"{API}/v5/market/funding/history?category=linear&symbol={symbol}&limit=200&startTime={start}&endTime={end}")
        lst = js["result"]["list"]
        if not lst:
            break
        rows += lst; end = min(int(x["fundingRateTimestamp"]) for x in lst) - 1; time.sleep(0.12)
        if len(lst) < 200:
            break
    if rows:
        d = pd.DataFrame(rows); d.index = pd.to_datetime(d["fundingRateTimestamp"].astype("int64"), unit="ms"); d.index.name = "time"
        d = d[["fundingRate"]].astype(float).rename(columns={"fundingRate": "funding_rate"})
        if old is not None:
            d = pd.concat([old, d])
        d = d[~d.index.duplicated(keep="last")].sort_index(); d.to_parquet(f)
        return len(d), d.index.min()
    return (len(old), old.index.min()) if old is not None else (0, None)


def spread(symbol, n=10, gap=20):
    sp, depth = [], []
    for k in range(n):
        try:
            ob = get(f"{API}/v5/market/orderbook?category=linear&symbol={symbol}&limit=1")["result"]
            b, a = ob["b"][0], ob["a"][0]; bid, ask = float(b[0]), float(a[0]); mid = (bid + ask) / 2
            sp.append((ask - bid) / mid * 1e4); depth.append(min(float(b[1]) * bid, float(a[1]) * ask))
        except Exception:
            pass
        if k < n - 1:
            time.sleep(gap)
    s = pd.Series(sp, dtype=float); d = pd.Series(depth, dtype=float)
    return (round(float(s.median()), 2) if len(s) else None, round(float(d.median())) if len(d) else None, len(s))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inst = instruments(); by = {}
    for r in inst:
        if r.get("status") == "Trading":
            by.setdefault(norm(r["baseCoin"]), []).append(r)
    rows = []
    for c in universe():
        cand = by.get(norm(c), [])
        r = sorted(cand, key=lambda x: len(x["symbol"]))[0] if cand else None
        rows.append({"coin": c, "listed": r is not None, "symbol": r["symbol"] if r else "",
                     "min_qty": r["lotSizeFilter"]["minOrderQty"] if r else "", "qty_step": r["lotSizeFilter"]["qtyStep"] if r else "",
                     "min_notional": r["lotSizeFilter"].get("minNotionalValue", "") if r else "", "tick": r["priceFilter"]["tickSize"] if r else "",
                     "max_leverage": r["leverageFilter"]["maxLeverage"] if r else "", "funding_interval_min": r.get("fundingInterval", "") if r else ""})
    I = pd.DataFrame(rows); I.to_csv(OUT / "instruments.csv", index=False)
    print(f"{int(I.listed.sum())} of {len(I)} coins have a trading USDT perpetual on Bybit; missing: {list(I.loc[~I.listed, 'coin'])}", flush=True)
    for _, r in I[I.listed].iterrows():
        try:
            n, first = funding(r.symbol); print(f"  funding {r.symbol}: {n} rows from {first}", flush=True)
        except Exception as e:
            print(f"  funding {r.symbol}: {e.__class__.__name__} (run again later)", flush=True)
    print("spreads: 10 snapshots per coin, 20 s apart (about 3 minutes per coin; all coins in parallel batches of 10) ...", flush=True)
    from concurrent.futures import ThreadPoolExecutor
    syms = list(I.loc[I.listed, "symbol"])
    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(spread, syms))
    S = pd.DataFrame({"symbol": syms, "spread_bp_median": [x[0] for x in res], "top_depth_usd_median": [x[1] for x in res],
                      "samples": [x[2] for x in res], "measured_utc": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M")})
    S.to_csv(OUT / "spreads.csv", index=False)
    print(S.sort_values("spread_bp_median").to_string(index=False), flush=True)
    print("done -> research_data/bybit (git add research_data/bybit, commit, push)", flush=True)


if __name__ == "__main__":
    main()

"""v9.9 R1c (research/v99/r1c_protocol.json): queue-aware fill check of the R1 limit orders with the live order-book logger.

Inputs: paper_trading/book_logs/<day>.csv.gz (top-5 Bybit book every 2 s, 23:59-00:12 UTC, book_logger_start.bat) and the v9.8 paper
orders at 00:00 UTC (paper_trading/v98/orders.csv), Bybit public trades of the same window (public.bybit.com, cached as in r1b_ticks.py).
Per order: our limit joins the back of the queue at the touch at t0 (first snapshot >= 00:00:00); it fills when taker volume AT our price
since t0 exceeds the queue ahead of us (size at the touch in the snapshot) plus our own size, or at once on a trade-through.
Gain in bp vs a taker order at t0, as in r1b. Writes results/v99/r1c_queue.json.
`--selftest` builds a fake log from a cached r1b tick day (code check only, no result is recorded)."""
import gzip
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "src"))
LOGS = ROOT / "paper_trading/book_logs"; W_MIN = 60


CACHE = ROOT / "hub_data/bybit_ticks"


def ticks(coin, day, minutes=75):
    """Bybit public trades of the first `minutes` of `day` (same cache and format as r1b_ticks.py, without importing that script)."""
    import requests, zlib
    f = CACHE / f"{coin}_{pd.Timestamp(day):%Y-%m-%d}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    url = f"https://public.bybit.com/trading/{coin}USDT/{coin}USDT{pd.Timestamp(day):%Y-%m-%d}.csv.gz"
    stop = (pd.Timestamp(day) + pd.Timedelta(minutes=minutes)).timestamp()
    r = requests.get(url, stream=True, timeout=60)
    if r.status_code != 200:
        return None
    z = zlib.decompressobj(16 + zlib.MAX_WBITS); buf = b""; rows = []
    for chunk in r.iter_content(1 << 16):
        buf += z.decompress(chunk); *lines, buf = buf.split(b"\n"); done = False
        for ln in lines:
            if not ln or ln.startswith(b"timestamp"):
                continue
            p = ln.split(b","); t = float(p[0])
            if t > stop:
                done = True; break
            rows.append((t, p[2] == b"Buy", float(p[3]), float(p[4])))
        if done:
            break
    r.close(); CACHE.mkdir(parents=True, exist_ok=True)
    d = pd.DataFrame(rows, columns=["t", "buy", "size", "price"]); d.to_parquet(f); return d


def evaluate(order_usd, side, snap, T, t0):
    """order_usd > 0; side +1 buy / -1 sell; snap: first book row >= t0 (dict); T: trades (t, buy, size, price)."""
    bid, ask = float(snap["b0_p"]), float(snap["a0_p"]); L = bid if side > 0 else ask
    q_ahead = float(snap["b0_q"] if side > 0 else snap["a0_q"]); own = order_usd / L
    w = T[(T.t > t0) & (T.t <= t0 + W_MIN * 60)]; e = T[T.t <= t0 + W_MIN * 60]
    if w.empty or e.empty:
        return None
    if side > 0:
        through = (w.price < L).any(); at = w[(~w.buy) & (w.price <= L)]
    else:
        through = (w.price > L).any(); at = w[(w.buy) & (w.price >= L)]
    queue_fill = at["size"].sum() >= q_ahead + own
    filled = bool(through or queue_fill)
    bW = e[~e.buy].price.iloc[-1] if (~e.buy).any() else bid; aW = e[e.buy].price.iloc[-1] if e.buy.any() else ask; PW = 0.5 * (bW + aW)
    entry0 = ask if side > 0 else bid; entryW = aW if side > 0 else bW
    base = side * (PW / entry0 - 1) - 5.5e-4
    cand = side * (PW / L - 1) - 2e-4 if filled else side * (PW / entryW - 1) - 5.5e-4
    return {"filled": filled, "by_trade_through": bool(through), "queue_ahead_usd": q_ahead * L, "gain_bp": (cand - base) * 1e4}


def run(orders: pd.DataFrame, log_for_day) -> dict:
    rows = []
    for (day, coin), g in orders.groupby(["day", "coin"]):
        L = log_for_day(day)
        if L is None:
            continue
        t0 = pd.Timestamp(day).timestamp(); s = L[(L.coin == coin) & (L.wall_ts >= t0)]
        if s.empty:
            continue
        T = ticks(coin, pd.Timestamp(day))
        if T is None or T.empty:
            continue
        usd = float(g["usd"].sum())
        r = evaluate(abs(usd), 1 if usd > 0 else -1, s.iloc[0], T, t0)
        if r:
            rows.append({"day": day, "coin": coin, "usd": usd, **r})
    R = pd.DataFrame(rows)
    if R.empty:
        return {"orders": 0}
    wm = lambda c: float(np.average(R[c], weights=R["usd"].abs()))
    return {"orders": len(R), "days": int(R.day.nunique()), "fill rate (queue model)": round(float(R.filled.mean()), 3),
            "of which by trade-through": round(float(R.by_trade_through.mean()), 3), "mean gain bp (notional-weighted)": round(wm("gain_bp"), 2),
            "median queue ahead USD": round(float(R.queue_ahead_usd.median())), "R1b reference (Bybit ticks, trade-through)": 2.99}


def main():
    if "--selftest" in sys.argv:
        day = "2025-05-05"; T = ticks("BTC", pd.Timestamp(day)); t0 = pd.Timestamp(day).timestamp()
        q = T[(T.t >= t0) & (T.t <= t0 + 5)]; bid = q[~q.buy].price.iloc[-1]; ask = q[q.buy].price.iloc[-1]
        fake = pd.DataFrame([{"wall_ts": t0 + 1, "coin": "BTC", "b0_p": bid, "b0_q": 3.0, "a0_p": ask, "a0_q": 3.0}])
        orders = pd.DataFrame([{"day": day, "coin": "BTC", "usd": 20000.0}, {"day": day, "coin": "BTC", "usd": 0.0}])
        print("SELFTEST (fake log, nothing recorded):", run(orders.iloc[:1], lambda d: fake)); return
    files = sorted(LOGS.glob("*.csv.gz"))
    if not files:
        sys.exit("no order-book logs yet (book_logger_start.bat on the PC, then share paper_trading/book_logs)")
    O = pd.read_csv(ROOT / "paper_trading/v98/orders.csv")
    O["ts"] = pd.to_datetime(O["hour_utc"]); O = O[O.ts.dt.hour == 0]; O["day"] = O.ts.dt.strftime("%Y-%m-%d")
    O["usd"] = O["usd"].astype(float) * np.where(O["side"].astype(str).str.upper().str.startswith("S"), -1, 1)
    def log_for_day(d):
        f = LOGS / f"{d}.csv.gz"
        return pd.read_csv(gzip.open(f, "rt")) if f.exists() else None
    out = run(O[["day", "coin", "usd"]], log_for_day)
    (ROOT / "results/v99/r1c_queue.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

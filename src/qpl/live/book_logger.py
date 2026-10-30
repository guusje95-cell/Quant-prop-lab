"""Read-only Bybit order-book logger around the daily 00:00 UTC rebalance (v9.9 R1 follow-up).

Every day from 23:59 to 00:12 UTC it polls the PUBLIC Bybit linear order book (top 5 levels) of the R1 limit coins every 2 seconds
and appends the snapshots to paper_trading/book_logs/<YYYY-MM-DD>.csv.gz. Together with Bybit's public trade files this gives the
queue ahead of a resting order at the touch, so R1's fills can be measured with a queue model instead of the trade-through bound.

No API key, no account, no orders: public market data only.

    python -m qpl.live.book_logger loop      # keep running (sleeps outside the window)
    python -m qpl.live.book_logger once      # one snapshot of every coin now (connectivity test)"""
import csv
import gzip
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "paper_trading" / "book_logs"
COINS = ["AAVE", "ADA", "ATOM", "AVAX", "BCH", "BNB", "BTC", "DOGE", "DOT", "ETC", "ETH", "FIL", "LINK", "LTC", "NEAR", "SOL", "TRX", "UNI", "XLM", "XRP"]
URL = "https://api.bybit.com/v5/market/orderbook"
WINDOW = (23 * 60 + 59, 12)                     # minutes after midnight: from 23:59 to 00:12 UTC
FIELDS = ["wall_ts", "book_ts", "coin"] + [f"{s}{i}_{k}" for s in ("b", "a") for i in range(5) for k in ("p", "q")]


def snapshot(sess: requests.Session, coin: str) -> dict | None:
    try:
        r = sess.get(URL, params={"category": "linear", "symbol": f"{coin}USDT", "limit": 5}, timeout=5).json()["result"]
    except Exception:                                                        # noqa: BLE001 - one missed snapshot is fine
        return None
    row = {"wall_ts": f"{time.time():.3f}", "book_ts": r.get("ts"), "coin": coin}
    for s in ("b", "a"):
        lv = r.get(s) or []
        for i in range(5):
            p, q = (lv[i] if i < len(lv) else (None, None))
            row[f"{s}{i}_p"], row[f"{s}{i}_q"] = p, q
    return row


def in_window(t: float) -> bool:
    m = int(t // 60) % 1440
    return m >= WINDOW[0] or m < WINDOW[1]


def day_file(t: float) -> Path:
    day = time.strftime("%Y-%m-%d", time.gmtime(t + 120))                    # the 23:59 snapshots belong to the next day's rebalance
    return OUT / f"{day}.csv.gz"


def poll_once(sess, t):
    OUT.mkdir(parents=True, exist_ok=True)
    f = day_file(t); new = not f.exists()
    with gzip.open(f, "at", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        if new:
            w.writeheader()
        for c in COINS:
            row = snapshot(sess, c)
            if row:
                w.writerow(row)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "loop"
    sess = requests.Session()
    if mode == "once":
        rows = [snapshot(sess, c) for c in COINS]
        ok = [r for r in rows if r and r["b0_p"]]
        print(f"{len(ok)} of {len(COINS)} coins answered; e.g. {ok[0]['coin']} bid {ok[0]['b0_p']} x {ok[0]['b0_q']} / ask {ok[0]['a0_p']} x {ok[0]['a0_q']}" if ok
              else "no answer from Bybit (blocked or offline?)")
        return
    print("Order-book logger running (23:59-00:12 UTC daily). Leave this window open. Ctrl+C to stop.", flush=True)
    while True:
        t = time.time()
        if in_window(t):
            poll_once(sess, t); time.sleep(max(0.0, 2.0 - (time.time() - t)))
        else:
            time.sleep(20)


if __name__ == "__main__":
    main()

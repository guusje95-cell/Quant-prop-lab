"""Export the logged-in MT5 terminal's own TICK history (bid / ask) for the symbols the CFD book trades, to
research_data/firm_ticks/<company>/<symbol>_<day>.parquet. READ-ONLY: no orders, no account data written.
Purpose: measure the firm's real spreads by time of day and simulate limit orders at the 00:00 UTC rebalance (CFD execution study).

    python scripts/mt5_export_ticks.py [--days 30]

Per day it keeps 23:00-02:00 UTC (the daily rebalance) for every symbol, and the full day for BTC/ETH (spread profile)."""
import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COINS = ["BTC", "ETH", "SOL", "XRP", "XDG", "BNB", "ADA", "LTC", "LINK", "AVAX", "DOT", "BCH", "XLM", "NEAR", "ETC", "UNI", "AAVE", "FIL"]
INDICES = ["US100.cash", "US500.cash", "US30.cash"]


def main():
    a = argparse.ArgumentParser(); a.add_argument("--days", type=int, default=30); x = a.parse_args()
    try:
        import MetaTrader5 as mt5
    except ImportError:
        sys.exit("MetaTrader5 package missing: pip install MetaTrader5")
    if not mt5.initialize():
        sys.exit(f"Could not connect to MT5 ({mt5.last_error()}): open MT5 and log in first")
    acc = mt5.account_info(); company = (acc.company if acc else "unknown").replace(" ", "_").replace("/", "_").replace(".", "")
    names = {s.name for s in (mt5.symbols_get() or [])}
    syms = [f"{c}/USD" for c in COINS if f"{c}/USD" in names] + [s for s in INDICES if s in names]
    out = ROOT / "research_data/firm_ticks" / company; out.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0); n = 0
    for k in range(1, x.days + 1):
        d = today - timedelta(days=k)
        for s in syms:
            mt5.symbol_select(s, True)
            full = s.split("/")[0] in ("BTC", "ETH")
            a0, a1 = (d, d + timedelta(days=1)) if full else (d - timedelta(hours=1), d + timedelta(hours=2))
            t = mt5.copy_ticks_range(s, a0, a1, mt5.COPY_TICKS_INFO)
            if t is None or len(t) == 0:
                continue
            df = pd.DataFrame(t)[["time_msc", "bid", "ask"]]; df["time"] = pd.to_datetime(df.pop("time_msc"), unit="ms")
            f = out / f"{s.replace('/', '').replace('.', '_')}_{d:%Y-%m-%d}.parquet"; df.to_parquet(f, index=False, compression="zstd"); n += 1
        print(f"{d:%Y-%m-%d}: done", flush=True)
    mt5.shutdown(); print(f"{n} files in {out}")


if __name__ == "__main__":
    main()

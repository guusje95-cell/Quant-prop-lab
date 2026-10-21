"""Deribit options trade history (free, public, no account) -> daily aggregates for BTC and ETH (options flow, put/call, skew).
Run on your own PC (history.deribit.com is not reachable from the cloud container):

    python -m qpl.live.deribit_options            # 2020-01-01 to yesterday, resumable (run again to continue)

Every option trade carries its implied vol, the index price, the instrument (expiry, strike, call/put) and the taker side.
Raw trades are NOT stored; each UTC day is reduced to one row per bucket:
    type (C/P) x moneyness K/S (<0.85, 0.85-0.95, 0.95-1.05, 1.05-1.15, >1.15) x tenor (<8d, 8-45d, >45d) x taker side (buy/sell)
with amount (coins), amount-weighted implied vol sum, trade count, block-trade amount.
Output: research_data/deribit_options/<COIN>_options_daily.parquet (a few MB). Paced at ~8 requests/s, well under the public limit."""
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from qpl.live.more_data import get

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "deribit_options"
START = datetime(2020, 1, 1, tzinfo=timezone.utc)
HOSTS = ("https://history.deribit.com", "https://www.deribit.com")
MNY = [0, 0.85, 0.95, 1.05, 1.15, 99]
TEN = [-1, 8, 45, 10000]


def _expiry(code):
    return datetime.strptime(code, "%d%b%y").replace(hour=8, tzinfo=timezone.utc)


def day_trades(coin, day):
    """All option trades of one UTC day (paged, oldest first)."""
    t0 = int(day.timestamp() * 1000); t1 = t0 + 86400000; rows, seen, start = [], set(), t0
    while True:
        js = None
        recent = day > datetime.now(timezone.utc) - timedelta(days=3)          # www.deribit.com keeps only recent trades
        for h in (HOSTS if recent else HOSTS[:1]):
            try:
                js = get(f"{h}/api/v2/public/get_last_trades_by_currency_and_time?currency={coin}&kind=option"
                         f"&start_timestamp={start}&end_timestamp={t1 - 1}&count=1000&sorting=asc&include_old=true"); break
            except Exception:
                js = None
        if js is None:
            raise RuntimeError("Deribit not reachable")
        tr = js["result"]["trades"]
        for x in tr:
            if x["trade_id"] not in seen:
                seen.add(x["trade_id"]); rows.append(x)
        if not js["result"].get("has_more") or not tr:
            break
        nxt = tr[-1]["timestamp"]
        start = nxt if nxt > start else start + 1
        time.sleep(0.12)
    return rows


def aggregate(rows, day):
    if not rows:
        return pd.DataFrame()
    d = pd.DataFrame(rows)
    parts = d["instrument_name"].str.split("-", expand=True)
    d["type"] = parts[3]; d["K"] = parts[2].astype(float)
    exp = parts[1].map(lambda c: _expiry(c))
    d["T"] = [(e - datetime.fromtimestamp(ts / 1000, tz=timezone.utc)).total_seconds() / 86400 for e, ts in zip(exp, d["timestamp"])]
    d["m"] = d["K"] / d["index_price"]
    d["mny"] = pd.cut(d["m"], MNY, labels=["<0.85", "0.85-0.95", "0.95-1.05", "1.05-1.15", ">1.15"], right=False).astype(str)
    d["ten"] = pd.cut(d["T"], TEN, labels=["<8d", "8-45d", ">45d"], right=False).astype(str)
    d["side"] = d["direction"]
    d["ivw"] = d["iv"].astype(float) * d["amount"].astype(float)
    d["block"] = np.where(d["block_trade_id"].notna(), d["amount"], 0.0) if "block_trade_id" in d.columns else 0.0
    g = d.groupby(["type", "mny", "ten", "side"]).agg(amount=("amount", "sum"), iv_sum=("ivw", "sum"), n=("trade_id", "count"), block=("block", "sum"))
    g = g.reset_index(); g.insert(0, "day", pd.Timestamp(day.date()))
    return g


def fetch(coin):
    OUT.mkdir(parents=True, exist_ok=True); f = OUT / f"{coin}_options_daily.parquet"
    old = pd.read_parquet(f) if f.exists() else None
    day = (old["day"].max().to_pydatetime().replace(tzinfo=timezone.utc) + timedelta(days=1)) if old is not None else START
    last = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    new = []
    while day <= last:
        try:
            rows = day_trades(coin, day)
        except Exception as e:
            print(f"  {coin} {day:%Y-%m-%d}: {e.__class__.__name__}, stopping here (run again later)", flush=True); break
        a = aggregate(rows, day)
        if len(a):
            new.append(a)
        if day.day == 1 or day == last:
            print(f"{coin} {day:%Y-%m-%d}: {len(rows)} trades", flush=True)
        day += timedelta(days=1)
        if len(new) >= 30:                                     # save every 30 days (resumable)
            old = _save(f, old, new); new = []
    _save(f, old, new)


def _save(f, old, new):
    if not new:
        return old
    d = pd.concat(([old] if old is not None else []) + new, ignore_index=True)
    d = d.drop_duplicates(["day", "type", "mny", "ten", "side"], keep="last").sort_values(["day", "type", "mny", "ten", "side"])
    d.to_parquet(f, index=False)
    return d


if __name__ == "__main__":
    for c in (sys.argv[1:] or ["BTC", "ETH"]):
        fetch(c)
    print("done", flush=True)

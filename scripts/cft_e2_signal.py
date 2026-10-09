"""Daily target positions for the CFT E2 LIQUID2 strategy (gen31; config/crypto_gen31_protocol.json).

Run once per day right after 00:00 UTC (before 00:05 UTC if possible), on your own machine:
    python scripts/cft_e2_signal.py --equity 100000 --program 1PHASE
It downloads PUBLIC Bybit USDT-perp daily candles (no API key, no account access, no orders), drops the still-open
candle, computes the frozen E2 signal for BTCUSDT and ETHUSDT and prints the target position (USDT notional and coin
quantity) per coin. You place / adjust the orders yourself. It never trades.
Offline check against the research data: --offline (uses data/processed Binance spot candles)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.strategies import cft_e2 as E  # noqa: E402

# L = v / (raw E2 LIQUID2 vol 2018-2022); frozen in gen31 (results/crypto_gen31_ev.json)
LEVER = {"1PHASE": 0.3203, "2PHASE": 0.4270}
COINS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}


def bybit_daily(symbol: str, limit: int = 400) -> pd.DataFrame:
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=D&limit={limit}"
    with urllib.request.urlopen(url, timeout=20) as r:
        rows = json.load(r)["result"]["list"]
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume", "turnover"]).astype(float)
    df.index = pd.to_datetime(df.pop("t").astype("int64"), unit="ms")
    df = df.sort_index()
    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    return df[df.index < today]                       # completed candles only


def targets(close: pd.DataFrame, L: float) -> pd.Series:
    w = E.raw_weights(close) * L
    return w.iloc[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--equity", type=float, required=True, help="current account equity in USDT")
    ap.add_argument("--program", choices=list(LEVER), default="1PHASE")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    if a.offline:
        from qpl.data import static_klines as SK
        close = SK.load("1d")["close"][list(COINS)].dropna()
    else:
        close = pd.DataFrame({k: bybit_daily(s)["close"] for k, s in COINS.items()}).dropna()
    if len(close) < 200:
        sys.exit("need >= 200 completed daily candles")
    w = targets(close, LEVER[a.program])
    print(f"signal date (last completed UTC day): {close.index[-1].date()}  program {a.program}  L={LEVER[a.program]}")
    for k in COINS:
        notional = w[k] * a.equity
        print(f"{COINS[k]:9s} weight {w[k]:+.4f}  target {notional:12,.2f} USDT  = {notional / close[k].iloc[-1]:.6f} {k}  (last close {close[k].iloc[-1]:,.2f})")
    print(f"gross exposure {w.abs().sum():.3f} x equity (long-only; never short; 0 = flat)")


if __name__ == "__main__":
    main()

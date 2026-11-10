"""Weiss-expiry timer (EX-1c, 2026-11-10): the Weiss sleeve's edge decays within minutes of 08:00 UTC (per trade, 114 trades 2022-26:
21.6 bp filled at 08:00, 19.2 bp at 08:01, 15.0 bp at 08:05, 13.9 bp at 08:15). The hourly book reaches the bot only at ~08:12-08:20,
so the bots run this timer themselves: on the last Friday of the month, at 08:00:0x UTC, side = -sign(price at 08:00 / open at 07:00 - 1)
per coin (BTC, ETH; exactly the paper rule in paper_v5.compute), sized like the book's Weiss part (side / 2 x the book's Weiss multiplier x
equity x risk), sent at market; at 10:00:0x the Weiss part goes to zero, again at market. Everything else stays with the hourly book.

Pure functions; prices come from the venue (bots pass a callable coin -> (open 07:00, price 08:00))."""
from __future__ import annotations

import numpy as np
import pandas as pd

WEISS = "Weiss expiry"
COINS = ("BTC", "ETH")
WAITING = "waiting for the 08:00 prices"
CAP_X_EQUITY = {"hyro": 1.0, "bf": 1.0, "propr": 1.0}   # cap on the Weiss gross in x account equity. WS-1 (2022-26): 1.5x / 2.5x cost no
                                                          # Sharpe; WS-1b (unseen 2020-21 days): at 1.5x one day fell through the 5% daily
                                                          # limit inside a minute despite the emergency stop, at 1.0x none -> 1.0x for all
ENTRY_MAX_MIN = 30                       # later than 08:30 the timer leaves the trade to the hourly book (no late chase)


def _utc(now: pd.Timestamp) -> pd.Timestamp:
    return now.tz_convert("UTC").tz_localize(None) if now.tzinfo else now


def is_weiss_day(t: pd.Timestamp) -> bool:
    d = _utc(t).normalize()
    return d.dayofweek == 4 and (d + pd.Timedelta(days=7)).month != d.month


def phase(now: pd.Timestamp) -> str | None:
    """'hold' from 08:00 to 10:00 UTC on a Weiss day, 'exit' from 10:00 to 12:00 (until the hourly book has caught up), else None"""
    n = _utc(now)
    if not is_weiss_day(n):
        return None
    t = n - n.normalize()
    if pd.Timedelta(hours=8) <= t < pd.Timedelta(hours=10):
        return "hold"
    if pd.Timedelta(hours=10) <= t < pd.Timedelta(hours=12):
        return "exit"
    return None


def next_event(now: pd.Timestamp) -> pd.Timestamp | None:
    """the next 08:00 / 10:00 UTC on a Weiss day within 40 days (for the bots' sleep)"""
    n = _utc(now)
    for k in range(41):
        d = n.normalize() + pd.Timedelta(days=k)
        if is_weiss_day(d):
            for h in (8, 10):
                t = d + pd.Timedelta(hours=h)
                if t > n:
                    return t
    return None


def sleep_seconds(now: pd.Timestamp, default: float = 300.0, lag: float = 3.0) -> float:
    """sleep the default loop interval, but wake `lag` seconds after a Weiss event if one comes sooner"""
    t = next_event(now)
    if t is None:
        return default
    s = (t - _utc(now)).total_seconds() + lag
    return max(1.0, min(default, s))


def active(book: dict) -> bool:
    """True while the timer has changed this book (the bots then skip the stale-book check: the Weiss legs do not depend on the hourly
    book's age, and every other target is unchanged from the book the bot already holds)"""
    return bool(book.get("weiss_overlay"))


def sleep_after(res: dict | None, now: pd.Timestamp, default: float = 300.0) -> float:
    """loop sleep: 5 s while the timer waits for the 08:00 prices; 30 s while the Weiss legs are open (WS-1: the daily stop must be
    watched inside the trade); else until the next Weiss event or the default interval"""
    if isinstance(res, dict) and (res.get("weiss_timer") or {}).get("weiss") == WAITING:
        return 5.0
    if phase(now) == "hold":
        return min(30.0, sleep_seconds(now, default))
    return sleep_seconds(now, default)


def cap_factor(m: float, account_risk: float | None, cap_x_equity: float | None) -> float:
    """scale for the Weiss part so that its gross (|m| x account risk, in x equity) stays <= the cap"""
    if not cap_x_equity or not account_risk or not m:
        return 1.0
    return float(min(1.0, cap_x_equity / (abs(float(m)) * float(account_risk))))


def apply(book: dict, now: pd.Timestamp, prices, state: dict, account_risk: float | None = None, cap_x_equity: float | None = None) -> tuple[dict, dict | None]:
    """book with its Weiss part replaced by the timer's (state['weiss'] keeps the sides for the day). Returns (book, info or None).
    prices(coin) -> (open_0700, price_0800) or None."""
    ph = phase(now)
    m = (book.get("sleeve_multipliers") or {}).get(WEISS)
    if ph is None or not m:
        return book, None
    n = _utc(now); day = str(n.date())
    w = state.get("weiss") if (state.get("weiss") or {}).get("day") == day else None
    if ph == "hold" and w is None:
        if n - n.normalize() > pd.Timedelta(hours=8, minutes=ENTRY_MAX_MIN):
            f = cap_factor(m, account_risk, cap_x_equity)               # no timer entry: the hourly book's Weiss part, but capped
            tgt = dict(book.get("target_notional_usd") or {}); by = book.get("by_sleeve_usd") or {}
            for c in COINS:
                cur = float((by.get(c) or {}).get(WEISS, 0.0))
                if cur and f < 1.0:
                    tgt[c] = round(tgt.get(c, 0.0) - cur * (1.0 - f), 2)
            b2 = dict(book, target_notional_usd=tgt, weiss_overlay={"phase": "book", "cap": round(f, 4)}) if f < 1.0 else book
            return b2, {"weiss": "entry window missed: left to the hourly book", "cap": round(f, 4)}
        side = {}
        for c in COINS:
            p = prices(c)
            if p and p[0] and p[1] and np.isfinite(p[0]) and np.isfinite(p[1]):
                side[c] = float(-np.sign(p[1] / p[0] - 1))
        if len(side) < len(COINS):                            # a price is not there yet (the 08:00 bar can lag a few seconds): nothing is
            return book, {"weiss": WAITING}                   # stored, the bot retries in a few seconds (until the entry window closes)
        w = {"day": day, "side": side, "entry_utc": str(n)}; state["weiss"] = w
    if w is None:                                             # exit phase without a timer entry today: nothing to override
        return book, None
    eqr = float(book["equity"]) * float(book["risk"]); f = cap_factor(m, account_risk, cap_x_equity)
    tgt = dict(book.get("target_notional_usd") or {}); by = book.get("by_sleeve_usd") or {}
    for c in COINS:
        cur = float((by.get(c) or {}).get(WEISS, 0.0))
        new = (w["side"].get(c, 0.0) / len(COINS)) * float(m) * f * eqr if ph == "hold" else 0.0
        v = tgt.get(c, 0.0) - cur + new
        if abs(v) > 1e-6:
            tgt[c] = round(v, 2)
        else:
            tgt.pop(c, None)
    return dict(book, target_notional_usd=tgt, weiss_overlay={"phase": ph, "side": w["side"], "cap": round(f, 4)}), {"weiss": ph, "side": w["side"], "cap": round(f, 4)}

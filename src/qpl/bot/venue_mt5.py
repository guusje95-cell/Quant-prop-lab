"""MT5 bridge for the CFD book (BrightFunded and other MT5 prop firms). DRY-RUN ONLY (task B1, 2026-11-02).

Runs on the user's Windows PC next to an MT5 terminal that is open and logged in (e.g. a BrightFunded trial / challenge account),
using the official MetaTrader5 Python package. Each pass: read the target book (default paper_trading/bf28cand/book_next_hour.json,
built by qpl.live.bf28_book; --candidate bf27 for the older book), scale to this account (equity x risk), cap gross crypto exposure at the 1:5 crypto leverage, apply the
no-trade band, convert USD targets to lots with the symbol's contract size / volume step, and VALIDATE every order with
mt5.order_check (margin, volume, symbol, market open) - nothing is sent. Positions are kept virtually in the state file, so the
dry-run behaves like a live account would. Guards: kill switch file, daily stop (2.5% of the initial balance from the day's start
equity, BrightFunded's daily reference = the higher of balance / equity at the rollover is approximated by start-of-day equity),
stale book, news blackout windows (config/news_blackouts.json, list of UTC times; no order within +-6 minutes: BrightFunded's
red-folder rule). Live order sending is deliberately NOT implemented (it needs the paper gate, the user's OK and the firm's rules).

    python -m qpl.bot.venue_mt5 --phase challenge            # one pass
    python -m qpl.bot.venue_mt5 --phase challenge --loop     # every 5 minutes (bot_bf27_mt5_dryrun.bat)"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import pandas as pd

from qpl.bot.adapters import Adapter
from qpl.bot.planner import apply_cap, plan_orders, scaled_targets
from qpl.bot import weiss_timer as WT
from qpl.bot.risk import Guard
from qpl.bot.rules import Rules
from qpl.bot.runner import log_orders
from qpl.bot.safety import MAX_STALE_HOURS, heartbeat, load_state, read_json, sanitize_targets, save_state, stale_flatten_due

ROOT = Path(__file__).resolve().parents[3]
BOOK = ROOT / "paper_trading/bf28cand/book_next_hour.json"          # 2026-11-10 (audit A-1): the bf2.8 candidate (was bf2.7)
BOOKS = {"bf28": ("bf28_book", ROOT / "paper_trading/bf28cand/book_next_hour.json"), "bf27": ("bf27_book", ROOT / "paper_trading/bf27cand/book_next_hour.json")}
STATE = ROOT / "bot_state_mt5"
ALIAS = {"XDG": "DOGE"}
FIAT = {"EUR", "GBP", "AUD", "NZD", "CAD", "CHF", "JPY", "USD", "HKD", "SGD", "MXN", "NOK", "SEK", "PLN", "ZAR", "DKK", "TRY", "XAU", "XAG", "XPT", "XPD"}
INDEX = {"US100": ("US100.cash", "USTEC", "NAS100"), "US500": ("US500.cash", "US500", "SPX500"), "US30": ("US30.cash", "US30", "DJ30"),
         "US2000": ("US2000.cash", "US2000", "RUS2000", "US2000Cash")}
CRYPTO_LEVERAGE = 5.0


def symbol_map(mt5) -> dict[str, str]:
    """book coin / index -> the firm's MT5 symbol ('BTC/USD', 'XDG/USD' -> DOGE, 'US100.cash' ...)."""
    names = [s.name for s in (mt5.symbols_get() or [])]
    out = {}
    for n in names:
        if "/" in n and n.split("/")[1].upper().startswith("USD"):
            base = n.split("/")[0].upper(); out.setdefault(ALIAS.get(base, base), n)
        elif n.upper().endswith("USD") and len(n) <= 9 and n[:-3].isalpha() and n[:-3].upper() not in FIAT:
            base = n[:-3].upper(); out.setdefault(ALIAS.get(base, base), n)
    for k, cands in INDEX.items():
        for c in cands:
            if c in names:
                out[k] = c; break
    return out


def lots(usd: float, price: float, contract: float, step: float, vmin: float) -> float:
    """signed lots for a USD notional, rounded DOWN in size to the volume step; 0 if below the minimum volume"""
    if price <= 0 or contract <= 0:
        return 0.0
    raw = abs(usd) / (price * contract); n = math.floor(raw / step + 1e-9) * step
    return 0.0 if n < vmin - 1e-12 else math.copysign(round(n, 8), usd)


def in_blackout(now: pd.Timestamp, path: Path = ROOT / "config/news_blackouts.json", minutes: int = 6) -> bool:
    if not path.exists():
        return False
    ts = [pd.Timestamp(x) for x in json.loads(path.read_text())]
    now = now.tz_localize(None) if now.tzinfo else now
    return any(abs((now - t).total_seconds()) <= minutes * 60 for t in ts)


def filling_mode(mt5, info) -> int:
    """the filling mode this symbol accepts (brokers differ: 'Unsupported filling mode' otherwise). symbol_info.filling_mode is a
    bitmask: 1 = FOK allowed, 2 = IOC allowed; neither -> RETURN (market execution)"""
    fm = int(getattr(info, "filling_mode", 0) or 0)
    if fm & 1:
        return getattr(mt5, "ORDER_FILLING_FOK", 0)
    if fm & 2:
        return getattr(mt5, "ORDER_FILLING_IOC", 1)
    return getattr(mt5, "ORDER_FILLING_RETURN", 2)


class MT5DryRun(Adapter):
    """prices / specs / order_check from the logged-in MT5 terminal; positions virtual (state); never sends an order"""
    name = "mt5-dryrun"

    def __init__(self, mt5, state: dict, initial_balance: float, symbols: dict[str, str]):
        self.m, self.s, self.sym = mt5, state, symbols
        self.s.setdefault("positions", {}); acc = mt5.account_info()
        self.s.setdefault("equity", float(acc.equity) if acc else initial_balance)

    def equity(self) -> float:
        return float(self.s["equity"])

    def positions(self) -> dict[str, float]:
        return dict(self.s["positions"])

    def _order(self, coin: str, usd: float, kind: str) -> dict:
        if coin not in self.sym:
            return {"coin": coin, "usd": usd, "filled_usd": 0.0, "how": "not listed at this firm: skipped"}
        sym = self.sym[coin]; self.m.symbol_select(sym, True); i = self.m.symbol_info(sym); t = self.m.symbol_info_tick(sym)
        if i is None or t is None or not t.ask or not t.bid:
            return {"coin": coin, "symbol": sym, "usd": usd, "filled_usd": 0.0, "how": "no quote: skipped"}
        price = t.ask if usd > 0 else t.bid; v = lots(usd, price, i.trade_contract_size, i.volume_step, i.volume_min)
        if v == 0:
            return {"coin": coin, "symbol": sym, "usd": usd, "filled_usd": 0.0, "how": "below the minimum volume: skipped"}
        req = {"action": self.m.TRADE_ACTION_DEAL, "symbol": sym, "volume": abs(v), "type": self.m.ORDER_TYPE_BUY if v > 0 else self.m.ORDER_TYPE_SELL,
               "price": price, "deviation": 20, "magic": 270227, "comment": f"bf27 dry-run {kind}", "type_filling": filling_mode(self.m, i)}
        chk = self.m.order_check(req)
        ok = chk is not None and chk.retcode in (0, getattr(self.m, "TRADE_RETCODE_DONE", 10009))
        filled = math.copysign(abs(v) * price * i.trade_contract_size, usd) if ok else 0.0
        if ok:
            p = self.s["positions"]; p[coin] = round(p.get(coin, 0.0) + filled, 2)
            if abs(p[coin]) < 1e-6:
                p.pop(coin)
        return {"coin": coin, "symbol": sym, "usd": usd, "lots": v, "price": price, "filled_usd": round(filled, 2),
                "how": f"{kind} (dry-run: order_check {'OK' if ok else 'REJECTED'} {getattr(chk, 'comment', '')})"}

    def place_market(self, coin, usd):
        return self._order(coin, usd, "market")

    def place_limit(self, coin, usd, ref_price=None, minutes=15):
        return self._order(coin, usd, f"limit {minutes} min")

    def cancel_all(self):
        return None

    def flatten(self):
        """close everything: one closing order per position (validated with order_check); the virtual position is removed in full,
        lot-rounding dust included (a live close goes by position ticket, which always closes the whole volume)"""
        out = [self.place_market(c, -v) for c, v in list(self.s["positions"].items())]
        self.s["positions"] = {}
        return out


def mt5_weiss_prices(mt5, smap: dict, now: pd.Timestamp):
    """coin -> (open of the 07:00 UTC H1 bar, open of the 08:00 UTC H1 bar) from the terminal. Server time may differ from UTC by whole
    hours: the offset is taken from the last tick. None unless the newest H1 bar is the current (08:00 UTC) one (a bar can be missing
    for a few seconds after the hour)."""
    n = now.tz_convert("UTC").tz_localize(None) if now.tzinfo else now
    def f(coin):
        sym = smap.get(coin)
        if not sym or not hasattr(mt5, "copy_rates_from_pos"):
            return None
        r = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 2); tk = mt5.symbol_info_tick(sym)
        if r is None or len(r) < 2 or tk is None or not getattr(tk, "time", 0):
            return None
        off = round((pd.Timestamp(int(tk.time), unit="s") - n).total_seconds() / 3600)
        t1 = pd.Timestamp(int(r[-1]["time"]), unit="s") - pd.Timedelta(hours=off)
        return (float(r[-2]["open"]), float(r[-1]["open"])) if t1 == n.floor("h") and t1.hour == 8 else None
    return f


def one_pass(mt5, book_path: Path, phase: str, rules: Rules, sdir: Path, now: pd.Timestamp | None = None, weiss: bool = True) -> dict:
    now = now or pd.Timestamp.now("UTC"); s = load_state(sdir); book = read_json(book_path)
    if book is None:                                                        # missing / truncated book file
        res = {'time': str(now), 'action': 'book unreadable: holding'}
        ad0 = MT5DryRun(mt5, s, rules.initial_balance, symbol_map(mt5))
        if (Path(sdir) / 'STOP').exists() or stale_flatten_due(s.get('last_good_book_utc'), now, bool(ad0.positions())):
            log_orders(sdir, [dict(r, time=str(now), reason='kill or book unreadable > {} h'.format(MAX_STALE_HOURS)) for r in ad0.flatten()]); res['action'] = 'kill switch / book unreadable too long: flatten'
        save_state(sdir, s); return res
    s['last_good_book_utc'] = book.get('made_at_utc')
    ad = MT5DryRun(mt5, s, rules.initial_balance, symbol_map(mt5))
    s["equity"] = float(book["equity"]) * rules.initial_balance / 200_000.0      # dry-run equity follows the CFD paper account
    g = Guard(rules, s, sdir / "STOP"); eq = ad.equity(); g.new_day(now, eq); res = {"time": str(now), "equity": eq, "venue": "mt5 dry-run"}
    winfo = None
    if weiss:                                                                # EX-1c: Weiss trade at 08:00:0x / 10:00:0x UTC, not with the book
        book, winfo = WT.apply(book, now, mt5_weiss_prices(mt5, symbol_map(mt5), now), s)
        if winfo:
            res["weiss_timer"] = winfo
    bid = f"{book.get('made_at_utc')}|stale:{','.join(book.get('event_positions_stale') or [])}|weiss:{book.get('weiss_overlay')}"
    if g.killed():
        res["action"] = "kill switch: flatten"; log_orders(sdir, [dict(r, time=str(now), reason="kill") for r in ad.flatten()])
    elif g.daily_stop_hit(eq):
        if ad.positions():
            log_orders(sdir, [dict(r, time=str(now), reason="daily stop") for r in ad.flatten()])
        res["action"] = "daily stop: flat until the next UTC day"
    elif bid == s.get("last_book"):
        res["action"] = "no new book"
    elif g.book_stale(book, now):
        res["action"] = f"book from {book['made_at_utc']} is stale: skipped"; s["last_book"] = bid
        if stale_flatten_due(book.get("made_at_utc"), now, bool(ad.positions())):
            log_orders(sdir, [dict(r, time=str(now), reason="book stale > 6 h") for r in ad.flatten()]); res["action"] += "; stale > 6 h: flatten"
    elif in_blackout(now):
        res["action"] = "news blackout window: waiting"
    else:
        risk = rules.risk_challenge if phase == "challenge" else rules.risk_funded
        tg, bad = sanitize_targets(scaled_targets(book, eq, risk)); res["dropped_non_finite"] = bad
        crypto = {c: v for c, v in tg.items() if c not in INDEX}; idx = {c: v for c, v in tg.items() if c in INDEX}
        tg = {**apply_cap(crypto, CRYPTO_LEVERAGE * eq * 0.98), **idx}                     # firm margin: crypto 1:5
        orders = plan_orders(tg, ad.positions(), rules.band_usd, rules.min_order_usd); fills = []
        lim = rules.limit_minutes_daily if pd.Timestamp(book["for_hour_utc"]).hour == 0 else rules.limit_minutes
        for o in orders:
            urgent = bool(book.get("weiss_overlay")) and o["coin"] in WT.COINS             # the Weiss legs cannot wait for a limit fill
            f = ad.place_market(o["coin"], o["usd"]) if (o["close"] or urgent) else ad.place_limit(o["coin"], o["usd"], None, lim)
            fills.append(dict(o, **f, time=str(now), for_hour=book["for_hour_utc"]))
        log_orders(sdir, fills); s["last_book"] = bid
        res.update(action=f"{len(orders)} orders", orders=len(orders), rejected=sum("REJECTED" in f.get("how", "") for f in fills),
                   skipped=sum("skipped" in f.get("how", "") for f in fills), gross_after=round(sum(abs(v) for v in ad.positions().values())))
    save_state(sdir, s); return res


def main():
    a = argparse.ArgumentParser(); a.add_argument("--phase", choices=["challenge", "funded"], default="challenge")
    a.add_argument("--candidate", choices=list(BOOKS), default="bf28"); a.add_argument("--book", default=None)
    a.add_argument("--state", default=str(STATE)); a.add_argument("--loop", action="store_true")
    a.add_argument("--account", type=float, default=200_000.0); x = a.parse_args()
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise SystemExit(f"Could not connect to MT5 ({mt5.last_error()}): open MT5 and log in first")
    rules = Rules(initial_balance=x.account)
    import importlib
    builder = importlib.import_module(f"qpl.live.{BOOKS[x.candidate][0]}"); x.book = x.book or str(BOOKS[x.candidate][1])
    from qpl.live import news_blackouts as NB                            # audit A-3: the blackout list did not exist (guard was inactive)
    nb_at = None
    try:
        while True:
            try:
                if nb_at is None or pd.Timestamp.now() - nb_at > pd.Timedelta(days=7):
                    print({"news_blackouts": NB.build()}, flush=True); nb_at = pd.Timestamp.now()
                builder.build()
                r = one_pass(mt5, Path(x.book), x.phase, rules, Path(x.state)); heartbeat(Path(x.state), r); print(r, flush=True)
            except Exception as e:                                       # noqa: BLE001 - keep the loop alive
                heartbeat(Path(x.state), None, str(e)); print({"error": str(e)}, flush=True)
            if not x.loop:
                break
            time.sleep(WT.sleep_seconds(pd.Timestamp.now(tz="UTC")))           # wakes at 08:00:03 / 10:00:03 on Weiss days
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()

"""v9.9 candidate bot runner, DRY-RUN ONLY (task 70; user-approved 'option a' 2026-11-02). Completely separate from v9.8:
own book (paper_trading/v99cand/book_next_hour.json, built by qpl.live.v99_book from the v9.8 paper book + the four event-sleeve
ledgers), own state folder (bot_state_v99cand/), no paper account, no keys, no orders sent. The v9.8 bot files (runner / planner / rules,
frozen) are not changed: this module reuses their pure functions and only generalises the low-cap caps to every event-short sleeve
listed in the book's 'lowcap_sleeves' (HyroTrader: 5% per coin, 4.5% of the initial balance in TOTAL).

    python -m qpl.bot.runner_v99 --phase challenge            # one pass
    python -m qpl.bot.runner_v99 --phase challenge --loop     # every 5 minutes (bot_v99_dryrun.bat)

Each pass: if the v9.8 book is new or an event sleeve's open positions are not yet for the book's hour, refresh the event sleeves
(qpl.live.coinbase_short.step, the same frozen-ledger step the hub job runs) and rebuild the v9.9 book; then the v9.8 bot rules apply
unchanged (scale to the account, gross cap, low-cap caps, band, limit 15 min / 60 min at 00:00 UTC, daily stop, kill switch
bot_state_v99cand/STOP, stale book)."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from qpl.bot import adapters
from qpl.bot import weiss_timer as WT
from qpl.bot.planner import apply_cap, plan_orders, scaled_targets
from qpl.bot.risk import Guard
from qpl.bot.rules import Rules
from qpl.bot.runner import log_orders
from qpl.bot.safety import MAX_STALE_HOURS, heartbeat, load_state, read_json, sanitize_targets, save_state, stale_flatten_due

ROOT = Path(__file__).resolve().parents[3]
BOOK = ROOT / "paper_trading/v99cand/book_next_hour.json"
STATE = ROOT / "bot_state_v99cand"


def lowcap_coins(book: dict) -> set[str]:
    sl = book.get("lowcap_sleeves") or ["listing short"]
    return {c for c, row in (book.get("by_sleeve_usd") or {}).items() if any(abs(row.get(s, 0.0)) > 0 for s in sl)}


def cap_lowcap(targets: dict[str, float], book: dict, per_coin_usd: float, total_usd: float) -> dict[str, float]:
    """per-coin cap, then the TOTAL cap pro rata over all event-short coins (same formulas as planner.cap_listing_coins / _total)."""
    lst = lowcap_coins(book)
    t = {c: (max(-per_coin_usd, min(per_coin_usd, v)) if c in lst and per_coin_usd > 0 else v) for c, v in targets.items()}
    g = sum(abs(v) for c, v in t.items() if c in lst)
    if total_usd <= 0 or g <= total_usd:
        return t
    k = total_usd / g
    return {c: (v * k if c in lst else v) for c, v in t.items()}


def book_id(book: dict) -> str:
    return f"{book.get('made_at_utc')}|stale:{','.join(book.get('event_positions_stale') or [])}|weiss:{book.get('weiss_overlay')}"


def refresh_book(log=print) -> dict | None:
    """rebuild the v9.9 book when needed; returns the book (None if the v9.8 book does not exist yet)."""
    from qpl.live import v99_book as VB
    src = ROOT / "paper_trading/v98/book_next_hour.json"
    if not src.exists():
        return None
    h1 = json.loads(src.read_text())["for_hour_utc"]
    old = json.loads(BOOK.read_text()) if BOOK.exists() else {}
    fresh = old.get("for_hour_utc") == h1 and old.get("made_at_utc") == json.loads(src.read_text())["made_at_utc"] and not old.get("event_positions_stale")
    if fresh:
        return old
    stale = []
    for _, (d, _) in VB.EVENT.items():
        f = ROOT / "paper_trading" / d / "open_positions.json"
        if not f.exists() or json.loads(f.read_text()).get("for_hour_utc") != str(pd.Timestamp(h1)):
            stale.append(d)
    if stale and pd.Timestamp.now(tz="UTC").tz_localize(None).floor("h") == pd.Timestamp(h1):
        try:
            from qpl.live import coinbase_short
            coinbase_short.step(log=lambda *a: None)
        except Exception as e:                                           # noqa: BLE001 - the book is still built (event sleeves flat)
            log(f"event sleeves not refreshed: {e}")
    return VB.build()


def bybit_weiss_prices(coin: str):
    """(open of the 07:00 1h bar, open of the 08:00 1h bar) of the Bybit USDT perp (public market data, no key); None if not available"""
    import urllib.request
    try:
        u = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={coin}USDT&interval=60&limit=2"
        rows = json.loads(urllib.request.urlopen(u, timeout=10).read())["result"]["list"]           # newest first
        if pd.Timestamp(int(rows[0][0]), unit="ms").hour != 8:
            return None
        return float(rows[1][1]), float(rows[0][1])
    except Exception:                                                    # noqa: BLE001 - no timer this time; the book still has Weiss
        return None


def one_pass(book_path: Path, phase: str, rules: Rules, sdir: Path, adapter_name: str = "dryrun", now: pd.Timestamp | None = None,
             prices=bybit_weiss_prices) -> dict:
    if adapter_name != "dryrun":
        raise SystemExit("v9.9 candidate: dry-run only (no live adapter until the user approves v9.9)")
    now = now or pd.Timestamp.now("UTC"); s = load_state(sdir)
    book = read_json(book_path)
    if book is None:                                                        # missing / truncated book file
        res = {'time': str(now), 'action': 'book unreadable: holding'}
        ad0 = adapters.DryRun(s, rules.initial_balance)
        if (Path(sdir) / 'STOP').exists() or stale_flatten_due(s.get('last_good_book_utc'), now, bool(ad0.positions())):
            log_orders(sdir, [dict(r, time=str(now), reason='kill or book unreadable > {} h'.format(MAX_STALE_HOURS)) for r in ad0.flatten()]); res['action'] = 'kill switch / book unreadable too long: flatten'
        save_state(sdir, s); return res
    s['last_good_book_utc'] = book.get('made_at_utc')
    ad = adapters.DryRun(s, rules.initial_balance)
    s["equity"] = float(book["equity"]) * rules.initial_balance / 200_000.0          # dry-run equity follows the v9.8 paper account
    g = Guard(rules, s, sdir / "STOP"); eq = ad.equity(); g.new_day(now, eq); res = {"time": str(now), "equity": eq, "book": "v99cand"}
    if prices is not None:                                                  # EX-1c: Weiss legs at 08:00:0x / 10:00:0x UTC
        book, winfo = WT.apply(book, now, prices, s, account_risk=rules.risk_challenge if phase == "challenge" else rules.risk_funded,
                               cap_x_equity=WT.CAP_X_EQUITY["hyro"])
        if winfo:
            res["weiss_timer"] = winfo
    if g.killed():
        res["action"] = "kill switch: flatten"; log_orders(sdir, [dict(r, time=str(now), reason="kill") for r in ad.flatten()])
    elif g.daily_stop_hit(eq):
        if ad.positions():
            log_orders(sdir, [dict(r, time=str(now), reason="daily stop") for r in ad.flatten()])
        res["action"] = "daily stop: flat until the next UTC day"
    elif book_id(book) == s.get("last_book"):
        res["action"] = "no new book"
    elif g.book_stale(book, now) and not (WT.active(book) and not stale_flatten_due(book.get("made_at_utc"), now, True)):
        res["action"] = f"book from {book['made_at_utc']} is stale: skipped"; s["last_book"] = book_id(book)
        if stale_flatten_due(book.get("made_at_utc"), now, bool(ad.positions())):
            log_orders(sdir, [dict(r, time=str(now), reason="book stale > 6 h") for r in ad.flatten()]); res["action"] += "; stale > 6 h: flatten"
    else:
        risk = rules.risk_challenge if phase == "challenge" else rules.risk_funded
        cap = (rules.gross_cap_challenge if phase == "challenge" else rules.gross_cap_funded) * rules.initial_balance
        tg, bad = sanitize_targets(scaled_targets(book, eq, risk)); res["dropped_non_finite"] = bad
        tg = cap_lowcap(apply_cap(tg, cap), book, rules.lowcap_cap_frac * rules.initial_balance,
                        rules.lowcap_total_frac * rules.initial_balance)
        orders = plan_orders(tg, ad.positions(), rules.band_usd, rules.min_order_usd); fills = []
        lim = rules.limit_minutes_daily if pd.Timestamp(book["for_hour_utc"]).hour == 0 else rules.limit_minutes
        for o in orders:
            urgent = bool(book.get("weiss_overlay")) and o["coin"] in WT.COINS
            f = ad.place_market(o["coin"], o["usd"]) if (o["close"] or urgent) else ad.place_limit(o["coin"], o["usd"], None, lim)
            fills.append(dict(o, **f, time=str(now), for_hour=book["for_hour_utc"], book="v99cand"))
        log_orders(sdir, fills); s["last_book"] = book_id(book)
        lc = lowcap_coins(book)
        res.update(action=f"{len(orders)} orders", orders=len(orders), gross_after=round(sum(abs(v) for v in ad.positions().values())),
                   lowcap_gross_after=round(sum(abs(v) for c, v in ad.positions().items() if c in lc)))
    save_state(sdir, s); return res


def main():
    a = argparse.ArgumentParser(); a.add_argument("--phase", choices=["challenge", "funded"], default="challenge")
    a.add_argument("--state", default=str(STATE)); a.add_argument("--loop", action="store_true"); a.add_argument("--account", type=float, default=200_000.0)
    x = a.parse_args(); rules = Rules(initial_balance=x.account)
    while True:
        r = None
        try:
            b = refresh_book()
            r = one_pass(BOOK, x.phase, rules, Path(x.state)) if b else {"action": "waiting for the v9.8 paper book"}
            heartbeat(Path(x.state), r); print(r, flush=True)
        except Exception as e:                                           # noqa: BLE001 - keep the loop alive
            heartbeat(Path(x.state), None, str(e)); print({"error": str(e)}, flush=True)
        if not x.loop:
            break
        time.sleep(WT.sleep_after(r, pd.Timestamp.now(tz="UTC")))


if __name__ == "__main__":
    main()

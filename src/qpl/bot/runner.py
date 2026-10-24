"""v8.6 bot runner (DRY-RUN). Run next to the paper trader on the same PC:

    python -m qpl.bot.runner --book paper_trading/v86/book_next_hour.json --phase challenge            # one pass
    python -m qpl.bot.runner --book paper_trading/v86/book_next_hour.json --phase challenge --loop     # every 5 minutes

Each new book (new made_at_utc) -> scale to this account, cap, band -> orders (limit 15 min, then market) -> log.
Guards: daily stop at -2.5% of the initial balance from the day's start equity (flatten, no trading until the next UTC day),
kill switch file bot_state/STOP, stale book (> 50 min old) skipped. Writes bot_state/state.json and bot_state/orders_log.csv."""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import pandas as pd
from qpl.bot.rules import Rules
from qpl.bot.planner import scaled_targets, apply_cap, plan_orders
from qpl.bot.risk import Guard
from qpl.bot import adapters

ROOT = Path(__file__).resolve().parents[3]


def load_state(d: Path) -> dict:
    f = d / "state.json"
    return json.loads(f.read_text()) if f.exists() else {}


def save_state(d: Path, s: dict):
    d.mkdir(parents=True, exist_ok=True); (d / "state.json").write_text(json.dumps(s, indent=1, default=str))


def log_orders(d: Path, rows: list[dict]):
    if rows:
        d.mkdir(parents=True, exist_ok=True); f = d / "orders_log.csv"; pd.DataFrame(rows).to_csv(f, mode="a", header=not f.exists(), index=False)


def one_pass(book_path: Path, phase: str, rules: Rules, sdir: Path, adapter_name: str = "dryrun", now: pd.Timestamp | None = None) -> dict:
    now = now or pd.Timestamp.now("UTC"); s = load_state(sdir)
    book = json.loads(book_path.read_text())
    ad = adapters.DryRun(s, rules.initial_balance) if adapter_name == "dryrun" else adapters.Bybit()
    if adapter_name == "dryrun":                                   # dry-run equity follows the paper account (same book, paper size $200k)
        s["equity"] = float(book["equity"]) * rules.initial_balance / 200_000.0
    g = Guard(rules, s, sdir / "STOP"); eq = ad.equity(); g.new_day(now, eq); res = {"time": str(now), "equity": eq}
    if g.killed():
        res["action"] = "kill switch: flatten"; log_orders(sdir, [dict(r, time=str(now), reason="kill") for r in ad.flatten()])
    elif g.daily_stop_hit(eq):
        if ad.positions():
            log_orders(sdir, [dict(r, time=str(now), reason="daily stop") for r in ad.flatten()])
        res["action"] = "daily stop: flat until the next UTC day"
    else:
        if book.get("made_at_utc") == s.get("last_book"):
            res["action"] = "no new book"
        elif g.book_stale(book, now):
            res["action"] = f"book from {book['made_at_utc']} is stale: skipped"; s["last_book"] = book.get("made_at_utc")
        else:
            risk = rules.risk_challenge if phase == "challenge" else rules.risk_funded
            cap = (rules.gross_cap_challenge if phase == "challenge" else rules.gross_cap_funded) * rules.initial_balance
            tg = apply_cap(scaled_targets(book, eq, risk), cap)
            orders = plan_orders(tg, ad.positions(), rules.band_usd, rules.min_order_usd); fills = []
            for o in orders:
                f = ad.place_market(o["coin"], o["usd"]) if o["close"] else ad.place_limit(o["coin"], o["usd"], None, rules.limit_minutes)
                fills.append(dict(o, **f, time=str(now), for_hour=book["for_hour_utc"]))
            for x in book.get("cascade_limit_orders") or []:
                fills.append({"time": str(now), "coin": x["coin"], "type": "cascade limit buy (separate order, 1 h)", "limit": x["limit_price"], "stop": x["stop"]})
            log_orders(sdir, fills); s["last_book"] = book.get("made_at_utc")
            res.update(action=f"{len(orders)} orders", gross_after=round(sum(abs(v) for v in ad.positions().values())), orders=len(orders))
    save_state(sdir, s); return res


def main():
    a = argparse.ArgumentParser(); a.add_argument("--book", default=str(ROOT / "paper_trading/v86/book_next_hour.json"))
    a.add_argument("--phase", choices=["challenge", "funded"], default="challenge"); a.add_argument("--state", default=str(ROOT / "bot_state"))
    a.add_argument("--adapter", default="dryrun"); a.add_argument("--loop", action="store_true"); a.add_argument("--account", type=float, default=200_000.0)
    x = a.parse_args(); rules = Rules(initial_balance=x.account)
    while True:
        print(one_pass(Path(x.book), x.phase, rules, Path(x.state), x.adapter), flush=True)
        if not x.loop:
            break
        time.sleep(300)


if __name__ == "__main__":
    main()

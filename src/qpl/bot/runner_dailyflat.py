"""DRY-RUN MT5 runner for the daily-flat equity-index book (DF-3 / DF-4) on index CFDs (US500 / US100 / US2000 / US30) at CFD prop
firms (FTMO / FundedNext / The5ers / BrightFunded type; EAs allowed). Flat 15:55-18:00 ET (over the 17:00 ET rollover: no swap) and
from Friday 15:55 ET to Sunday 18:00 ET. Targets: paper_trading/futuresdf/targets_session.json (scripts/v99/dailyflat_targets.py),
'before 14:00 ET' / 'after 14:00 ET' (R1 switch). Orders are only VALIDATED with mt5.order_check (venue_mt5.MT5DryRun); nothing is
sent. Live order sending is deliberately NOT implemented.

    python -m qpl.bot.runner_dailyflat --loop --risk 1.0 --max-cost 1     # bot_dailyflat_mt5_dryrun.bat"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

from qpl.bot.planner import plan_orders
from qpl.bot.risk import Guard
from qpl.bot.rules import Rules
from qpl.bot.runner import log_orders
from qpl.bot.safety import MAX_STALE_HOURS, heartbeat, load_state, read_json, sanitize_targets, save_state, stale_flatten_due
from qpl.bot.safety import gross_cap

ROOT = Path(__file__).resolve().parents[3]
TARGETS = ROOT / "paper_trading/futuresdf/targets_session.json"
STATE = ROOT / "bot_state_dailyflat"
INDEX = ("US500", "US100", "US2000", "US30")


def _et(now_utc: pd.Timestamp) -> pd.Timestamp:
    now_utc = now_utc if now_utc.tzinfo else now_utc.tz_localize("UTC")
    return now_utc.tz_convert("America/New_York").tz_localize(None)


FLAT_FROM = 15 * 60 + 55                                                     # futures firms; CFD firms (swap at 17:00 ET): 16 * 60 + 55


def flat_window(now_et: pd.Timestamp, flat_from: int | None = None) -> bool:
    ff = FLAT_FROM if flat_from is None else flat_from
    m = now_et.hour * 60 + now_et.minute; wd = now_et.weekday()
    if wd == 5 or (wd == 6 and m < 18 * 60) or (wd == 4 and m >= ff):
        return True
    return ff <= m < 18 * 60


def session_of(now_et: pd.Timestamp) -> pd.Timestamp:
    d = now_et.normalize() + (pd.Timedelta(days=1) if now_et.hour >= 18 else pd.Timedelta(0))
    while d.weekday() >= 5:
        d += pd.Timedelta(days=1)
    return d


def current_targets(tj: dict, now_utc: pd.Timestamp, flat_from: int | None = None) -> dict | None:
    """fractions of equity per index CFD for now; {} when the bot must be flat; None when the targets file is not for this session"""
    et = _et(now_utc)
    if flat_window(et, flat_from):
        return {}
    if et.hour == 16:                                                     # only reached when flat_from is after 16:00 (CFD firms)
        return tj.get("targets_1600_1655et") or {} if tj.get("block_date") == str(et.date()) else {}
    s = session_of(et)
    if tj.get("session") != str(s.date()):
        return None
    after = et.normalize() == s and et.hour >= 14
    if after:
        return tj["targets_after_14et"] if tj.get("targets_after_14et") is not None else tj["targets_before_14et"]   # no 14:05 refresh: keep R1's previous w
    return tj["targets_before_14et"]


def one_pass(mt5, tpath: Path, risk: float, rules: Rules, sdir: Path, now: pd.Timestamp | None = None, flat_from: int | None = None) -> dict:
    from qpl.bot.venue_mt5 import MT5DryRun, symbol_map
    now = now or pd.Timestamp.now("UTC"); s = load_state(sdir)
    ad = MT5DryRun(mt5, s, rules.initial_balance, {k: v for k, v in symbol_map(mt5).items() if k in INDEX})
    g = Guard(rules, s, sdir / "STOP"); eq = ad.equity(); g.new_day(now, eq); res = {"time": str(now), "et": str(_et(now)), "venue": "mt5 dry-run (daily-flat index book)"}
    tj = read_json(tpath) or {}                                             # missing / truncated targets: flat (current_targets -> None -> {})
    if g.killed():
        res["action"] = "kill switch: flatten"; log_orders(sdir, [dict(r, time=str(now), reason="kill") for r in ad.flatten()])
    elif g.daily_stop_hit(eq):
        if ad.positions():
            log_orders(sdir, [dict(r, time=str(now), reason="daily stop") for r in ad.flatten()])
        res["action"] = "daily stop: flat until the next day"
    else:
        fr = current_targets(tj, now, flat_from)
        if fr is None:
            res["action"] = f"no targets for this session (file is for {tj.get('session')}): holding flat"
            fr = {}
        fr, bad = sanitize_targets(fr); res["dropped_non_finite"] = bad
        tg, capped = gross_cap({c: v * eq * risk for c, v in fr.items()}, 3.0 * eq * risk)   # sanity: the book's gross never needs > 3x equity x risk
        res["gross_capped"] = capped
        orders = plan_orders(tg, ad.positions(), rules.band_usd, rules.min_order_usd); fills = []
        for o in orders:
            f = ad.place_market(o["coin"], o["usd"]); fills.append(dict(o, **f, time=str(now), session=tj.get("session")))
        log_orders(sdir, fills)
        s["positions"] = {k: v for k, v in s["positions"].items() if abs(v) >= rules.min_order_usd}   # lot-rounding dust (a live close is by ticket)
        res.setdefault("action", f"{len(orders)} orders" + (" (flat window)" if flat_window(_et(now), flat_from) else ""))
        res.update(orders=len(orders), rejected=sum("REJECTED" in f.get("how", "") for f in fills), gross_after=round(sum(abs(v) for v in ad.positions().values())))
    save_state(sdir, s); return res


def refresh(max_cost: float, log=print):
    """Databento top-up (paid; at most max_cost dollars, 0 = no download) + targets for the current / next session"""
    if max_cost > 0:
        r = subprocess.run([sys.executable, "-m", "qpl.live.databento_update", "--max-cost", str(max_cost)], cwd=ROOT, capture_output=True, text=True)
        log({"databento_update": r.stdout.strip().splitlines()[-1:] if r.stdout else r.stderr[-300:]})
    import os
    r = subprocess.run([sys.executable, str(ROOT / "scripts/v99/dailyflat_targets.py")], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ))
    log({"targets": "ok" if r.returncode == 0 else r.stderr[-500:]})


def main():
    a = argparse.ArgumentParser(); a.add_argument("--loop", action="store_true"); a.add_argument("--risk", type=float, default=1.0)
    a.add_argument("--account", type=float, default=100_000.0); a.add_argument("--max-cost", type=float, default=0.0)
    a.add_argument("--cfd-1655", action="store_true", help="CFD firms: hold until 16:55 ET (swap at 17:00), flat 16:55-18:00")
    a.add_argument("--targets", default=str(TARGETS)); a.add_argument("--state", default=str(STATE)); x = a.parse_args()
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise SystemExit(f"Could not connect to MT5 ({mt5.last_error()}): open MT5 and log in first")
    rules = Rules(initial_balance=x.account, band_usd=0.002 * x.account, min_order_usd=0.0005 * x.account)
    done = set()
    try:
        while True:
            try:
                et = _et(pd.Timestamp.now("UTC")); key = (str(et.date()), "1405" if (et.hour == 14 and et.minute >= 5) else "1605" if (et.hour == 16 and et.minute >= 5) else "")
                if key[1] and key not in done and et.weekday() < 5:
                    refresh(x.max_cost); done.add(key)
                r = one_pass(mt5, Path(x.targets), x.risk, rules, Path(x.state), flat_from=16 * 60 + 55 if x.cfd_1655 else None)
                heartbeat(Path(x.state), r); print(r, flush=True)
            except Exception as e:                                       # noqa: BLE001 - keep the loop alive
                heartbeat(Path(x.state), None, str(e)); print({"error": str(e)}, flush=True)
            if not x.loop:
                break
            time.sleep(300)
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()

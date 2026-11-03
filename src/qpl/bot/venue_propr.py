"""Propr (prop firm on Hyperliquid) bridge for the crypto book, DRY-RUN ONLY (task B2, 2026-11-03).

Built from Propr's official Bot API docs (github.com/XBorgLabs/propr-docs: REST https://api.propr.xyz/v1, header X-API-Key, account
endpoints /accounts/{accountId}/..., per-asset leverage limits /leverage-limits/effective, fee 0.075% per side). This module only sends
GET requests (account, positions, margin-config availability check, leverage limits) and the public Hyperliquid meta (size decimals);
it NEVER posts an order. Positions are kept virtually in the state file. Live order sending is deliberately NOT implemented.

Book: the v9.9 candidate (paper_trading/v99cand/book_next_hour.json); coins Propr / Hyperliquid does not list are skipped and logged.
Rules: risk 1.0 (Propr's drawdown is trailing; Gen329 / M1), per-asset notional <= its leverage limit x equity (cross margin),
event-short coins in total <= 4.5% of the initial balance (same safety as the HyroTrader version), band, daily stop, kill switch.

    set PROPR_API_KEY in the window only (bot_propr_dryrun.bat asks for it; never in a file or in chat)
    python -m qpl.bot.venue_propr --loop"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

import pandas as pd
import requests

from qpl.bot.adapters import Adapter
from qpl.bot.planner import plan_orders, scaled_targets
from qpl.bot.risk import Guard
from qpl.bot.rules import Rules
from qpl.bot.runner import log_orders
from qpl.bot.safety import MAX_STALE_HOURS, heartbeat, load_state, read_json, sanitize_targets, save_state, stale_flatten_due
from qpl.bot.runner_v99 import cap_lowcap

ROOT = Path(__file__).resolve().parents[3]
BOOK = ROOT / "paper_trading/v99cand/book_next_hour.json"
STATE = ROOT / "bot_state_propr"
API = os.environ.get("PROPR_API_URL", "https://api.propr.xyz/v1")
HL = "https://api.hyperliquid.xyz/info"


class ProprReader:
    """read-only Propr client (GET only)"""

    def __init__(self, key: str, session=None):
        self.s = session or requests.Session(); self.s.headers.update({"X-API-Key": key, "Content-Type": "application/json"})
        self.account_id = None

    def get(self, path: str, params=None, ok404: bool = False):
        r = self.s.get(API + path, params=params, timeout=30)
        if ok404 and r.status_code == 404:
            return None
        r.raise_for_status(); return r.json()

    def setup(self) -> str:
        d = self.get("/challenge-attempts", {"status": "active"}); items = d.get("data", d) if isinstance(d, dict) else d
        if not items:
            raise SystemExit("no active Propr challenge attempt on this API key")
        self.account_id = items[0]["accountId"]; return self.account_id

    def equity(self) -> float:
        a = self.get(f"/accounts/{self.account_id}"); a = a.get("data", a)
        return float(a.get("balance", 0)) + float(a.get("totalUnrealizedPnl", 0)) + float(a.get("isolatedPositionMargin", 0))

    def positions(self) -> dict[str, float]:
        d = self.get(f"/accounts/{self.account_id}/positions", {"status": "open", "limit": 200}); out = {}
        for p in d.get("data", d):
            q = float(p.get("quantity") or 0)
            if q:
                out[p["asset"]] = out.get(p["asset"], 0.0) + (1 if p["positionSide"] == "long" else -1) * q * float(p.get("markPrice") or 0)
        return out

    def tradable(self, asset: str) -> bool:
        return self.get(f"/accounts/{self.account_id}/margin-config/{asset}", ok404=True) is not None

    def leverage_limits(self) -> dict:
        return self.get("/leverage-limits/effective")


def hl_meta(session=None) -> dict[str, dict]:
    """asset -> {szDecimals, px} from the public Hyperliquid info API (mark prices from metaAndAssetCtxs)"""
    s = session or requests
    meta, ctx = s.post(HL, json={"type": "metaAndAssetCtxs"}, timeout=30).json()
    return {u["name"]: {"sz": int(u.get("szDecimals", 0)), "px": float(c.get("markPx") or 0)} for u, c in zip(meta["universe"], ctx) if not u.get("isDelisted")}


def hl_name(coin: str) -> str:
    """book coin -> Hyperliquid name (1000PEPE -> kPEPE)"""
    return "k" + coin[4:] if coin.startswith("1000") else coin


def max_lev(limits: dict, asset: str) -> float:
    return float((limits.get("overrides") or {}).get(asset, (limits.get("defaults") or {}).get("crypto", limits.get("defaultMax", 2))))


def qty(usd: float, px: float, sz: int) -> float:
    if px <= 0:
        return 0.0
    q = math.floor(abs(usd) / px * 10 ** sz) / 10 ** sz
    return 0.0 if q * px < 10 else math.copysign(q, usd)                   # Hyperliquid minimum order value $10


class ProprDryRun(Adapter):
    name = "propr-dryrun"

    def __init__(self, reader: ProprReader | None, state: dict, meta: dict, initial_balance: float):
        self.r, self.s, self.meta = reader, state, meta
        self.s.setdefault("positions", {}); self.s.setdefault("equity", initial_balance)

    def equity(self) -> float:
        return float(self.s["equity"])

    def positions(self) -> dict[str, float]:
        return dict(self.s["positions"])

    def _order(self, coin, usd, kind):
        a = hl_name(coin); m = self.meta.get(a)
        if m is None or (self.r is not None and not self.r.tradable(a)):
            return {"coin": coin, "usd": usd, "filled_usd": 0.0, "how": "not tradable at Propr / Hyperliquid: skipped"}
        q = qty(usd, m["px"], m["sz"])
        if q == 0:
            return {"coin": coin, "asset": a, "usd": usd, "filled_usd": 0.0, "how": "below the $10 minimum: skipped"}
        filled = round(q * m["px"], 2); p = self.s["positions"]; p[coin] = round(p.get(coin, 0.0) + filled, 2)
        if abs(p[coin]) < 1e-6:
            p.pop(coin)
        return {"coin": coin, "asset": a, "usd": usd, "qty": q, "px": m["px"], "filled_usd": filled, "fee_usd": round(abs(filled) * 0.00075, 2),
                "how": f"{kind} (dry-run: would POST /accounts/{{id}}/orders, nothing sent)"}

    def place_market(self, coin, usd):
        return self._order(coin, usd, "market")

    def place_limit(self, coin, usd, ref_price=None, minutes=15):
        return self._order(coin, usd, f"limit GTX {minutes} min")

    def cancel_all(self):
        return None

    def flatten(self):
        """close everything; the virtual position is removed in full (a live close uses reduce-only for the whole size)"""
        out = [self.place_market(c, -v) for c, v in list(self.s["positions"].items())]
        self.s["positions"] = {}
        return out


def one_pass(reader, meta, limits, book_path: Path, rules: Rules, sdir: Path, now: pd.Timestamp | None = None) -> dict:
    now = now or pd.Timestamp.now("UTC"); s = load_state(sdir); book = read_json(book_path)
    if book is None:                                                        # missing / truncated book file
        res = {'time': str(now), 'action': 'book unreadable: holding'}
        ad0 = ProprDryRun(reader, s, meta, rules.initial_balance)
        if (Path(sdir) / 'STOP').exists() or stale_flatten_due(s.get('last_good_book_utc'), now, bool(ad0.positions())):
            log_orders(sdir, [dict(r, time=str(now), reason='kill or book unreadable > {} h'.format(MAX_STALE_HOURS)) for r in ad0.flatten()]); res['action'] = 'kill switch / book unreadable too long: flatten'
        save_state(sdir, s); return res
    s['last_good_book_utc'] = book.get('made_at_utc')
    ad = ProprDryRun(reader, s, meta, rules.initial_balance)
    s["equity"] = float(book["equity"]) * rules.initial_balance / 200_000.0
    g = Guard(rules, s, sdir / "STOP"); eq = ad.equity(); g.new_day(now, eq); res = {"time": str(now), "equity": eq, "venue": "propr dry-run"}
    bid = f"{book.get('made_at_utc')}|stale:{','.join(book.get('event_positions_stale') or [])}"
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
    else:
        tg, bad = sanitize_targets(scaled_targets(book, eq, 1.0)); res["dropped_non_finite"] = bad    # Propr: risk 1.0 (trailing drawdown)
        tg = {c: max(-max_lev(limits, hl_name(c)) * eq * 0.95, min(max_lev(limits, hl_name(c)) * eq * 0.95, v)) for c, v in tg.items()}
        tg = cap_lowcap(tg, book, rules.lowcap_cap_frac * rules.initial_balance, rules.lowcap_total_frac * rules.initial_balance)
        orders = plan_orders(tg, ad.positions(), rules.band_usd * 0.5, rules.min_order_usd); fills = []      # $100k account: half the band
        lim = rules.limit_minutes_daily if pd.Timestamp(book["for_hour_utc"]).hour == 0 else rules.limit_minutes
        for o in orders:
            f = ad.place_market(o["coin"], o["usd"]) if o["close"] else ad.place_limit(o["coin"], o["usd"], None, lim)
            fills.append(dict(o, **f, time=str(now), for_hour=book["for_hour_utc"]))
        log_orders(sdir, fills); s["last_book"] = bid
        res.update(action=f"{len(orders)} orders", orders=len(orders), skipped=sum("skipped" in f.get("how", "") for f in fills),
                   gross_after=round(sum(abs(v) for v in ad.positions().values())))
    save_state(sdir, s); return res


def main():
    a = argparse.ArgumentParser(); a.add_argument("--loop", action="store_true"); a.add_argument("--account", type=float, default=100_000.0)
    a.add_argument("--book", default=str(BOOK)); a.add_argument("--state", default=str(STATE)); x = a.parse_args()
    key = os.environ.get("PROPR_API_KEY"); reader = None
    if key:
        reader = ProprReader(key); reader.setup()
    rules = Rules(initial_balance=x.account)
    while True:
        try:
            from qpl.bot import runner_v99
            runner_v99.refresh_book()
            limits = reader.leverage_limits() if reader else requests.get(API + "/leverage-limits/effective", timeout=30).json()
            r = one_pass(reader, hl_meta(), limits, Path(x.book), rules, Path(x.state)); heartbeat(Path(x.state), r); print(r, flush=True)
        except Exception as e:                                           # noqa: BLE001
            heartbeat(Path(x.state), None, str(e)); print({"error": str(e)}, flush=True)
        if not x.loop:
            break
        time.sleep(300)


if __name__ == "__main__":
    main()

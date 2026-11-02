"""MT5 bridge (dry-run): symbol mapping, lot rounding, order_check only (never order_send), crypto leverage cap, news blackout."""
import json
from types import SimpleNamespace as NS

import pandas as pd

from qpl.bot import venue_mt5 as V
from qpl.bot.rules import Rules


class FakeMT5:
    TRADE_ACTION_DEAL, ORDER_TYPE_BUY, ORDER_TYPE_SELL, ORDER_FILLING_IOC, TRADE_RETCODE_DONE = 1, 0, 1, 1, 10009

    def __init__(self):
        self.syms = {"BTC/USD": (1.0, 0.01, 0.01, 60000.0), "ETH/USD": (1.0, 0.01, 0.01, 3000.0), "XDG/USD": (1.0, 1.0, 1.0, 0.2),
                     "US100.cash": (1.0, 0.1, 0.1, 20000.0), "EURUSD": (100000.0, 0.01, 0.01, 1.1)}
        self.checks = []; self.sent = []

    def symbols_get(self):
        return [NS(name=n) for n in self.syms]

    def symbol_select(self, s, on):
        return True

    def symbol_info(self, s):
        c, step, vmin, _ = self.syms[s]; return NS(trade_contract_size=c, volume_step=step, volume_min=vmin)

    def symbol_info_tick(self, s):
        p = self.syms[s][3]; return NS(bid=p * 0.9999, ask=p * 1.0001)

    def account_info(self):
        return NS(equity=200000.0)

    def order_check(self, req):
        self.checks.append(req); return NS(retcode=0, comment="Done")

    def order_send(self, req):                                           # must never be called
        self.sent.append(req); raise AssertionError("order_send called in dry-run")


def test_symbol_map_and_lots():
    m = V.symbol_map(FakeMT5())
    assert m["BTC"] == "BTC/USD" and m["DOGE"] == "XDG/USD" and m["US100"] == "US100.cash" and "EUR" not in m
    assert V.lots(1000.0, 60000.0, 1.0, 0.01, 0.01) == 0.01
    assert V.lots(-599.0, 60000.0, 1.0, 0.01, 0.01) == 0.0                     # below the minimum volume
    assert V.lots(-1250.0, 0.2, 1.0, 1.0, 1.0) == -6250.0


def _book(tmp, tg, made="2026-11-03 10:05:00"):
    b = {"for_hour_utc": "2026-11-03 10:00:00", "made_at_utc": made, "equity": 200000.0, "risk": 2.0, "target_notional_usd": tg}
    p = tmp / "book.json"; p.write_text(json.dumps(b)); return p


def test_dry_run_checks_never_sends_and_caps(tmp_path):
    mt5 = FakeMT5(); now = pd.Timestamp("2026-11-03 10:10", tz="UTC")
    tg = {"BTC": 1_500_000.0, "ETH": -500_000.0, "US100": 300_000.0, "SOL": 50_000.0}
    r = V.one_pass(mt5, _book(tmp_path, tg), "challenge", Rules(risk_challenge=2.0), tmp_path / "st", now=now)
    assert mt5.sent == [] and len(mt5.checks) == 3                                # SOL not listed: skipped, no check
    st = json.loads((tmp_path / "st/state.json").read_text())
    crypto = sum(abs(v) for c, v in st["positions"].items() if c != "US100")
    assert crypto <= 5.0 * 200000 * 0.98 + 1 and abs(st["positions"]["US100"] - 300_000) < 3000
    assert r["skipped"] == 1 and r["rejected"] == 0


def test_news_blackout(tmp_path, monkeypatch):
    f = tmp_path / "nb.json"; f.write_text(json.dumps(["2026-11-03 19:00:00"]))
    assert V.in_blackout(pd.Timestamp("2026-11-03 19:04", tz="UTC"), f) and not V.in_blackout(pd.Timestamp("2026-11-03 19:10", tz="UTC"), f)

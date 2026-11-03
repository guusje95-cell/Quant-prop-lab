"""Failure-mode tests for the bots (2026-11-03): corrupt state, unreadable / stale books, NaN targets, kill switch, daily stop,
daylight-saving switches, runaway targets, missing quotes, heartbeat. Every scenario must end in a defined, safe state."""
import json
import math

import pandas as pd

from qpl.bot import runner_dailyflat as RD
from qpl.bot import runner_v99 as RV
from qpl.bot import safety as S
from qpl.bot import venue_mt5 as V
from qpl.bot import venue_propr as P
from qpl.bot.rules import Rules
from tests.test_mt5_bridge import FakeMT5

NOW = pd.Timestamp("2026-11-03 10:10", tz="UTC")


def _book(tmp, tg, made="2026-11-03 10:05:00", name="book.json"):
    b = {"for_hour_utc": "2026-11-03 10:00:00", "made_at_utc": made, "equity": 200000.0, "risk": 1.5, "target_notional_usd": tg,
         "by_sleeve_usd": {}, "lowcap_sleeves": []}
    p = tmp / name; p.write_text(json.dumps(b)); return p


def test_state_atomic_backup_and_corrupt_recovery(tmp_path):
    d = tmp_path / "st"
    S.save_state(d, {"positions": {"BTC": 1000.0}}); S.save_state(d, {"positions": {"BTC": 2000.0}})
    (d / "state.json").write_text('{"positions": {"BTC": 30')                        # crash while writing: truncated file
    s = S.load_state(d)
    assert s["positions"] == {"BTC": 1000.0} and s["_recovered_from_backup"]        # the last good state
    (d / "state.json.bak").write_text("garbage")
    assert S.load_state(d) == {"_state_missing_or_corrupt": True}                   # both broken: start flat, flagged


def test_v99_unreadable_book_holds_then_flattens(tmp_path):
    rules = Rules(); st = tmp_path / "st"
    RV.one_pass(_book(tmp_path, {"BTC": 300000.0}), "challenge", rules, st, now=NOW)
    pos = json.loads((st / "state.json").read_text())["positions"]; assert pos.get("BTC", 0) > 0
    bp = tmp_path / "book.json"; bp.write_text('{"for_hour_utc": "2026-11-03 11:00:00", "made_')    # truncated by a crashed writer
    r = RV.one_pass(bp, "challenge", rules, st, now=NOW + pd.Timedelta(hours=1))
    assert r["action"].startswith("book unreadable") and json.loads((st / "state.json").read_text())["positions"]   # recent: hold
    r = RV.one_pass(bp, "challenge", rules, st, now=NOW + pd.Timedelta(hours=7))
    assert "flatten" in r["action"] and json.loads((st / "state.json").read_text())["positions"] == {}            # > 6 h: flat


def test_v99_stale_book_flattens_after_6h(tmp_path):
    rules = Rules(); st = tmp_path / "st"
    RV.one_pass(_book(tmp_path, {"ETH": -200000.0}), "challenge", rules, st, now=NOW)
    old = _book(tmp_path, {"ETH": -200000.0}, made="2026-11-03 10:06:00", name="old.json")         # same content, never refreshed
    r = RV.one_pass(old, "challenge", rules, st, now=NOW + pd.Timedelta(hours=7))
    assert "stale > 6 h: flatten" in r["action"] and json.loads((st / "state.json").read_text())["positions"] == {}


def test_v99_nan_target_closes_that_coin_only(tmp_path):
    rules = Rules(); st = tmp_path / "st"
    RV.one_pass(_book(tmp_path, {"BTC": 300000.0, "ETH": 100000.0}), "challenge", rules, st, now=NOW)
    r = RV.one_pass(_book(tmp_path, {"BTC": float("nan"), "ETH": 100000.0}, made="2026-11-03 11:05:00"), "challenge", rules, st,
                    now=NOW + pd.Timedelta(hours=1))
    pos = json.loads((st / "state.json").read_text())["positions"]
    assert r["dropped_non_finite"] == ["BTC"] and "BTC" not in pos and pos.get("ETH", 0) > 0


def test_v99_daily_stop_flat_until_next_day(tmp_path):
    rules = Rules(); st = tmp_path / "st"
    RV.one_pass(_book(tmp_path, {"BTC": 300000.0}), "challenge", rules, st, now=NOW)
    crash = _book(tmp_path, {"BTC": 300000.0}, made="2026-11-03 12:05:00"); b = json.loads(crash.read_text()); b["equity"] = 190000.0
    crash.write_text(json.dumps(b))                                                  # -5% on the paper account: below the 2.5% stop
    r = RV.one_pass(crash, "challenge", rules, st, now=NOW + pd.Timedelta(hours=2))
    assert r["action"].startswith("daily stop") and json.loads((st / "state.json").read_text())["positions"] == {}
    r = RV.one_pass(_book(tmp_path, {"BTC": 300000.0}, made="2026-11-03 13:05:00"), "challenge", rules, st, now=NOW + pd.Timedelta(hours=3))
    assert r["action"].startswith("daily stop")                                      # stays flat the same UTC day
    r = RV.one_pass(_book(tmp_path, {"BTC": 300000.0}, made="2026-11-04 00:05:00"), "challenge", rules, st,
                    now=pd.Timestamp("2026-11-04 00:10", tz="UTC"))
    assert not r["action"].startswith("daily stop")                                  # next day: trading again


def test_mt5_stale_and_no_quote(tmp_path):
    mt5 = FakeMT5(); st = tmp_path / "st"; rules = Rules(risk_challenge=1.5)
    V.one_pass(mt5, _book(tmp_path, {"BTC": 100000.0}), "challenge", rules, st, now=NOW)
    assert json.loads((st / "state.json").read_text())["positions"]
    r = V.one_pass(mt5, _book(tmp_path, {"BTC": 100000.0}, name="b2.json", made="2026-11-03 10:06:00"), "challenge", rules, st,
                   now=NOW + pd.Timedelta(hours=8))
    assert "flatten" in r["action"] and json.loads((st / "state.json").read_text())["positions"] == {}
    mt5.symbol_info_tick = lambda s: None                                            # terminal lost its quotes
    r = V.one_pass(mt5, _book(tmp_path, {"BTC": 100000.0}, name="b3.json", made="2026-11-03 18:05:00"), "challenge", rules, st,
                   now=pd.Timestamp("2026-11-03 18:10", tz="UTC"))
    assert mt5.sent == [] and json.loads((st / "state.json").read_text())["positions"] == {}   # skipped, no crash, nothing opened


def test_propr_unreadable_book_no_crash(tmp_path):
    meta = {"BTC": {"sz": 5, "px": 60000.0}}; lim = {"defaults": {"crypto": 2}, "overrides": {"BTC": 10}}
    bp = tmp_path / "missing.json"
    r = P.one_pass(None, meta, lim, bp, Rules(initial_balance=100_000.0), tmp_path / "st", now=NOW)
    assert r["action"].startswith("book unreadable")


def test_dailyflat_kill_dst_and_runaway_target(tmp_path):
    mt5 = FakeMT5(); mt5.syms["US500.cash"] = (1.0, 0.1, 0.1, 6000.0); st = tmp_path / "st"
    rules = Rules(initial_balance=100_000.0, band_usd=200.0, min_order_usd=50.0)
    tj = {"session": "2026-11-04", "targets_before_14et": {"US500": 50.0, "US100": float("inf")}, "targets_after_14et": None}
    p = tmp_path / "t.json"; p.write_text(json.dumps(tj).replace("Infinity", "1e999"))
    u = lambda et: pd.Timestamp(et).tz_localize("America/New_York").tz_convert("UTC")
    r = RD.one_pass(mt5, p, 1.0, rules, st, now=u("2026-11-04 10:00"))
    pos = json.loads((st / "state.json").read_text())["positions"]
    assert r["gross_capped"] and sum(abs(v) for v in pos.values()) <= 3.0 * 100_000 * 1.0 + 1          # 50x equity capped to 3x (entered account 100k)
    assert "US100" not in pos and mt5.sent == []                                                        # inf dropped
    (st / "STOP").write_text("x")
    r = RD.one_pass(mt5, p, 1.0, rules, st, now=u("2026-11-04 10:05"))
    assert r["action"].startswith("kill") and json.loads((st / "state.json").read_text())["positions"] == {}
    # daylight-saving switches: US clocks change 2026-03-08 and 2026-11-01; the windows follow New York time
    assert RD.flat_window(pd.Timestamp("2026-03-09 15:56")) and not RD.flat_window(pd.Timestamp("2026-03-09 15:54"))
    assert RD._et(pd.Timestamp("2026-03-09 19:56", tz="UTC")).hour == 15 and RD._et(pd.Timestamp("2026-11-02 20:56", tz="UTC")).hour == 15
    assert RD.session_of(pd.Timestamp("2026-11-01 18:05")) == pd.Timestamp("2026-11-02")             # Sunday evening = Monday session


def test_heartbeat_counts_errors(tmp_path):
    S.heartbeat(tmp_path, {"action": "ok"}); S.heartbeat(tmp_path, None, "boom"); s = S.heartbeat(tmp_path, None, "boom")
    assert s["consecutive_errors"] == 2 and not s["ok"] and s["last_ok_utc"]
    assert S.heartbeat(tmp_path, {"action": "ok"})["consecutive_errors"] == 0


def test_sanitize_and_cap_helpers():
    g, bad = S.sanitize_targets({"A": 1.0, "B": float("nan"), "C": "x", "D": -2.0})
    assert g == {"A": 1.0, "D": -2.0} and set(bad) == {"B", "C"}
    t, c = S.gross_cap({"A": 300.0, "B": -100.0}, 200.0); assert c and math.isclose(sum(abs(v) for v in t.values()), 200.0)


def test_mt5_filling_mode_per_symbol():
    from types import SimpleNamespace as NS
    m = NS(ORDER_FILLING_FOK=0, ORDER_FILLING_IOC=1, ORDER_FILLING_RETURN=2)
    assert V.filling_mode(m, NS(filling_mode=1)) == 0 and V.filling_mode(m, NS(filling_mode=2)) == 1
    assert V.filling_mode(m, NS(filling_mode=3)) == 0 and V.filling_mode(m, NS(filling_mode=0)) == 2 and V.filling_mode(m, NS()) == 2

"""EX-1c Weiss timer: day / phase logic, sizing like the paper book, override of the book's Weiss part, entry window, bot integration."""
import json
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd

from qpl.bot import runner_v99 as RV
from qpl.bot import venue_mt5 as V
from qpl.bot import weiss_timer as WT
from qpl.bot.rules import Rules
from tests.test_mt5_bridge import FakeMT5


def _book(tg, by=None, m=2.0, hour="2026-11-27 07:00:00", made="2026-11-27 07:12:00"):
    return {"for_hour_utc": hour, "made_at_utc": made, "equity": 200000.0, "risk": 2.0, "target_notional_usd": tg,
            "by_sleeve_usd": by or {}, "sleeve_multipliers": {"Weiss expiry": m}, "lowcap_sleeves": []}


def test_days_and_phases():
    assert WT.is_weiss_day(pd.Timestamp("2026-11-27")) and not WT.is_weiss_day(pd.Timestamp("2026-11-20"))
    assert WT.phase(pd.Timestamp("2026-11-27 08:00:03")) == "hold" and WT.phase(pd.Timestamp("2026-11-27 10:00:03")) == "exit"
    assert WT.phase(pd.Timestamp("2026-11-27 07:59")) is None and WT.phase(pd.Timestamp("2026-11-26 08:30")) is None
    assert WT.next_event(pd.Timestamp("2026-11-10 12:00")) == pd.Timestamp("2026-11-27 08:00")
    assert WT.sleep_seconds(pd.Timestamp("2026-11-27 07:58:00")) == 123.0 and WT.sleep_seconds(pd.Timestamp("2026-11-10")) == 300.0


def test_entry_override_and_exit():
    st = {}
    px = {"BTC": (100.0, 101.0), "ETH": (50.0, 49.0)}                       # BTC up -> short, ETH down -> long
    b, info = WT.apply(_book({"BTC": 1000.0}), pd.Timestamp("2026-11-27 08:00:03"), px.get, st)
    k = 2.0 * 200000.0 * 2.0 / 2                                             # multiplier x equity x risk x 1/2 per coin
    assert info["side"] == {"BTC": -1.0, "ETH": 1.0} and np.isclose(b["target_notional_usd"]["BTC"], 1000.0 - k)
    assert np.isclose(b["target_notional_usd"]["ETH"], k)
    # the hourly book arrives with the Weiss part already in it: replaced, not doubled
    bk = _book({"BTC": 1000.0 - k, "ETH": k}, by={"BTC": {"Weiss expiry": -k}, "ETH": {"Weiss expiry": k}}, hour="2026-11-27 08:00:00")
    b2, _ = WT.apply(bk, pd.Timestamp("2026-11-27 08:15"), lambda c: None, st)
    assert np.isclose(b2["target_notional_usd"]["BTC"], 1000.0 - k) and np.isclose(b2["target_notional_usd"]["ETH"], k)
    b3, i3 = WT.apply(bk, pd.Timestamp("2026-11-27 10:00:03"), lambda c: None, st)       # exit: Weiss part to zero at once
    assert i3["weiss"] == "exit" and np.isclose(b3["target_notional_usd"]["BTC"], 1000.0) and "ETH" not in b3["target_notional_usd"]


def test_late_start_leaves_it_to_the_book():
    b, info = WT.apply(_book({"BTC": 5.0}), pd.Timestamp("2026-11-27 08:45"), lambda c: (1.0, 2.0), {})
    assert info["weiss"].startswith("entry window missed") and b["target_notional_usd"] == {"BTC": 5.0}


def test_runner_sends_weiss_at_market(tmp_path):
    p = tmp_path / "b.json"; p.write_text(json.dumps(_book({"SOL": 20000.0})))
    st = tmp_path / "st"; px = {"BTC": (100.0, 101.0), "ETH": (50.0, 51.0)}
    r = RV.one_pass(p, "challenge", Rules(), st, now=pd.Timestamp("2026-11-27 08:00:03", tz="UTC"), prices=px.get)
    assert r["weiss_timer"]["side"] == {"BTC": -1.0, "ETH": -1.0}
    import csv
    rows = list(csv.DictReader(open(st / "orders_log.csv")))
    assert {x["coin"] for x in rows if "market" in x.get("how", "").lower()} >= {"BTC", "ETH"}


def test_mt5_prices_need_the_current_bar():
    m = FakeMT5(); m.TIMEFRAME_H1 = 16385
    t8, t7 = int(pd.Timestamp("2026-11-27 08:00").timestamp()), int(pd.Timestamp("2026-11-27 07:00").timestamp())
    m.copy_rates_from_pos = lambda s, tf, a, n: [{"time": t7, "open": 100.0}, {"time": t8, "open": 101.0}]
    m.symbol_info_tick = lambda s: NS(bid=1, ask=1, time=t8 + 3)
    f = V.mt5_weiss_prices(m, {"BTC": "BTC/USD"}, pd.Timestamp("2026-11-27 08:00:03"))
    assert f("BTC") == (100.0, 101.0)
    m.copy_rates_from_pos = lambda s, tf, a, n: [{"time": t7 - 3600, "open": 99.0}, {"time": t7, "open": 100.0}]   # 08:00 bar not there yet
    assert f("BTC") is None


def test_propr_bot_uses_the_timer(tmp_path):
    from qpl.bot import venue_propr as P
    p = tmp_path / "b.json"; p.write_text(json.dumps(_book({"SOL": 20000.0})))
    meta = {"BTC": {"sz": 5, "px": 60000.0}, "ETH": {"sz": 4, "px": 3000.0}, "SOL": {"sz": 2, "px": 150.0}}
    lim = {"defaults": {"crypto": 2}, "overrides": {"BTC": 10, "ETH": 10, "SOL": 10}}
    px = {"BTC": (100.0, 99.0), "ETH": (50.0, 51.0)}
    r = P.one_pass(None, meta, lim, p, Rules(initial_balance=100_000.0), tmp_path / "st", now=pd.Timestamp("2026-11-27 08:00:04", tz="UTC"), prices=px.get)
    assert r["weiss_timer"]["side"] == {"BTC": 1.0, "ETH": -1.0}


def test_missing_price_is_retried_not_stored():
    st = {}
    b, info = WT.apply(_book({"BTC": 1000.0}), pd.Timestamp("2026-11-27 08:00:03"), {"BTC": (100.0, 101.0)}.get, st)
    assert info == {"weiss": WT.WAITING} and "weiss" not in st and b["target_notional_usd"] == {"BTC": 1000.0}
    assert WT.sleep_after({"weiss_timer": info}, pd.Timestamp("2026-11-27 08:00:03")) == 5.0
    b, info = WT.apply(_book({"BTC": 1000.0}), pd.Timestamp("2026-11-27 08:00:09"), {"BTC": (100.0, 101.0), "ETH": (50.0, 50.5)}.get, st)
    assert info["side"] == {"BTC": -1.0, "ETH": -1.0} and st["weiss"]["day"] == "2026-11-27"


def test_weiss_legs_trade_even_when_the_hourly_book_is_old(tmp_path):
    p = tmp_path / "b.json"; p.write_text(json.dumps(_book({"SOL": 20000.0}, made="2026-11-27 07:05:00")))     # 55 min old at 08:00
    st = tmp_path / "st"; px = {"BTC": (100.0, 101.0), "ETH": (50.0, 51.0)}
    r = RV.one_pass(p, "challenge", Rules(), st, now=pd.Timestamp("2026-11-27 08:00:03", tz="UTC"), prices=px.get)
    assert "orders" in r["action"] and "stale" not in r["action"]
    pos = json.loads((st / "state.json").read_text())["positions"]; assert pos["BTC"] < 0 and pos["ETH"] < 0
    r = RV.one_pass(p, "challenge", Rules(), st, now=pd.Timestamp("2026-11-27 10:00:03", tz="UTC"), prices=px.get)   # exit, book 3 h old
    pos = json.loads((st / "state.json").read_text())["positions"]; assert abs(pos.get("BTC", 0)) < 1 and abs(pos.get("ETH", 0)) < 1


def test_cap_on_the_weiss_gross():
    assert WT.cap_factor(2.0, 1.5, 1.5) == 0.5 and WT.cap_factor(0.8, 1.5, 1.5) == 1.0 and WT.cap_factor(2.0, None, 1.5) == 1.0
    px = {"BTC": (100.0, 101.0), "ETH": (50.0, 51.0)}
    b, info = WT.apply(_book({}, m=2.0), pd.Timestamp("2026-11-27 08:00:03"), px.get, {}, account_risk=1.5, cap_x_equity=1.5)
    full = 2.0 * 200000.0 * 2.0 / 2
    assert info["cap"] == 0.5 and np.isclose(b["target_notional_usd"]["BTC"], -full * 0.5)
    # at the account: |BTC| + |ETH| scaled to equity x risk 1.5 = 1.5 x equity
    k = (100000.0 * 1.5) / (200000.0 * 2.0); gross = sum(abs(v) for v in b["target_notional_usd"].values()) * k
    assert np.isclose(gross, 1.5 * 100000.0)
    # timer missed: the hourly book's own Weiss part is capped too
    bk = _book({"BTC": -full, "ETH": -full}, by={"BTC": {"Weiss expiry": -full}, "ETH": {"Weiss expiry": -full}}, m=2.0, hour="2026-11-27 08:00:00")
    b2, i2 = WT.apply(bk, pd.Timestamp("2026-11-27 08:40"), px.get, {}, account_risk=1.5, cap_x_equity=1.5)
    assert np.isclose(b2["target_notional_usd"]["BTC"], -full * 0.5) and i2["cap"] == 0.5


def test_loop_checks_every_30s_while_the_legs_are_open():
    assert WT.sleep_after({}, pd.Timestamp("2026-11-27 08:30")) == 30.0 and WT.sleep_after({}, pd.Timestamp("2026-11-27 12:30")) == 300.0

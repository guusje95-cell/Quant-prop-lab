"""Dry-run bot: planner rules equal the research execution; cap, daily stop, stale book, kill switch."""
import json
import numpy as np
import pandas as pd
from qpl.bot.planner import scaled_targets, apply_cap, plan_orders
from qpl.bot.rules import Rules
from qpl.bot.runner import one_pass


def research_band(A, b):
    """Gen327 sim() execution loop (fractions of the traded notional)."""
    E = np.zeros_like(A); cur = np.zeros(A.shape[1])
    for i in range(len(A)):
        ch = np.abs(A[i] - cur) >= b; ch |= (A[i] == 0) & (cur != 0); cur = np.where(ch, A[i], cur); E[i] = cur
    return E


def test_band_equals_research():
    rng = np.random.default_rng(1); A = np.round(rng.normal(0, 3000, (300, 6)), 2); A[rng.random(A.shape) < 0.2] = 0.0
    E = research_band(A, 1000.0); pos = {}
    coins = [f"C{j}" for j in range(6)]
    for i in range(len(A)):
        tg = dict(zip(coins, A[i]))
        for o in plan_orders(tg, pos, 1000.0, 0.0):
            pos[o["coin"]] = round(pos.get(o["coin"], 0.0) + o["usd"], 2)
        assert np.allclose([pos.get(c, 0.0) for c in coins], E[i], atol=0.02)


def test_scale_and_cap():
    book = {"equity": 200000.0, "risk": 2.0, "target_notional_usd": {"BTC": 100000.0, "ETH": -300000.0}}
    t = scaled_targets(book, 100000.0, 1.5); assert abs(t["BTC"] - 37500.0) < 1e-6 and abs(t["ETH"] + 112500.0) < 1e-6
    c = apply_cap({"A": 300000.0, "B": -200000.0}, 380000.0); assert abs(sum(abs(v) for v in c.values()) - 380000.0) < 1e-6
    assert apply_cap({"A": 1.0}, 0.0) == {"A": 1.0}


def _book(tmp, equity=200000.0, made="2026-10-24 10:05:00", tg=None):
    b = {"for_hour_utc": "2026-10-24 10:00:00", "made_at_utc": made, "equity": equity, "risk": 2.0,
         "target_notional_usd": tg or {"BTC": 50000.0, "ETH": -20000.0, "SOL": 500.0}, "cascade_limit_orders": []}
    p = tmp / "book.json"; p.write_text(json.dumps(b)); return p


def test_runner_dryrun_and_guards(tmp_path):
    r = Rules(risk_challenge=2.0); now = pd.Timestamp("2026-10-24 10:10:00", tz="UTC"); sd = tmp_path / "st"
    res = one_pass(_book(tmp_path), "challenge", r, sd, now=now)
    st = json.loads((sd / "state.json").read_text())
    assert res["orders"] == 2 and st["positions"] == {"BTC": 50000.0, "ETH": -20000.0}          # SOL 500 < band
    assert one_pass(_book(tmp_path), "challenge", r, sd, now=now)["action"] == "no new book"
    # equity falls 3% of the initial balance below the day's start -> flatten and stay flat
    res = one_pass(_book(tmp_path, equity=194000.0, made="2026-10-24 11:05:00"), "challenge", r, sd, now=pd.Timestamp("2026-10-24 11:10:00", tz="UTC"))
    assert res["action"].startswith("daily stop") and json.loads((sd / "state.json").read_text())["positions"] == {}
    # next UTC day trades again; a stale book is skipped
    res = one_pass(_book(tmp_path, equity=194000.0, made="2026-10-25 00:05:00"), "funded", r, sd, now=pd.Timestamp("2026-10-25 01:30:00", tz="UTC"))
    assert "stale" in res["action"]
    res = one_pass(_book(tmp_path, equity=194000.0, made="2026-10-25 01:05:00"), "funded", r, sd, now=pd.Timestamp("2026-10-25 01:10:00", tz="UTC"))
    assert res["orders"] == 2
    (sd / "STOP").write_text("stop"); res = one_pass(_book(tmp_path, made="2026-10-25 02:05:00"), "funded", r, sd, now=pd.Timestamp("2026-10-25 02:10:00", tz="UTC"))
    assert res["action"].startswith("kill") and json.loads((sd / "state.json").read_text())["positions"] == {}


def test_cap_listing_coins():
    from qpl.bot.planner import cap_listing_coins
    book = {"by_sleeve_usd": {"NEWX": {"listing short": -3000.0}, "BTC": {"C*": 50000.0}}}
    out = cap_listing_coins({"NEWX": -25000.0, "BTC": 80000.0}, book, 10000.0)
    assert out == {"NEWX": -10000.0, "BTC": 80000.0}

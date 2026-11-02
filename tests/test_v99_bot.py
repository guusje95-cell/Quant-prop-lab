"""v9.9 candidate dry-run bot (task 70): event-sleeve positions without lookahead, the v9.9 book builder, total low-cap cap over all
event sleeves, and complete separation from the v9.8 paper files."""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from qpl.bot import runner_v99 as RV
from qpl.bot.rules import Rules
from qpl.live import coinbase_short as CB
from qpl.live import v99_book as VB

ROOT = Path(__file__).resolve().parents[1]


def _closes(n=300, start="2026-11-01 00:00", jump_at=None):
    ix = pd.date_range(start, periods=n, freq="h"); px = np.full(n, 100.0)
    if jump_at is not None:
        px[jump_at:] = 131.0
    return pd.Series(px, index=ix)


def test_position_at_window_and_stop():
    cl = _closes(); T = pd.Timestamp("2026-11-01 10:20")                  # entry bar 11:00, short from 12:00 for 168 h
    assert CB.position_at(cl, T, None, 168, pd.Timestamp("2026-11-01 11:00")) == 0.0
    assert CB.position_at(cl, T, None, 168, pd.Timestamp("2026-11-01 12:00")) == -CB.SIZE
    assert CB.position_at(cl, T, None, 168, pd.Timestamp("2026-11-08 11:00")) == -CB.SIZE   # last held bar = entry + 168 h
    assert CB.position_at(cl, T, None, 168, pd.Timestamp("2026-11-08 12:00")) == 0.0
    late = pd.Timestamp("2026-11-01 15:30")                               # detected late: entry = close of the detection bar
    assert CB.position_at(cl, T, late, 168, pd.Timestamp("2026-11-01 15:00")) == 0.0
    assert CB.position_at(cl, T, late, 168, pd.Timestamp("2026-11-01 16:00")) == -CB.SIZE
    st = _closes(jump_at=30)                                              # close of bar 30 (06:00 day 2) >= +30%: out from bar 31
    assert CB.position_at(st, T, None, 168, pd.Timestamp("2026-11-02 06:00")) == -CB.SIZE
    assert CB.position_at(st, T, None, 168, pd.Timestamp("2026-11-02 07:00")) == 0.0


def test_position_at_no_lookahead():
    """bars that close at or after the hour being decided never change the decision"""
    cl = _closes(); T = pd.Timestamp("2026-11-01 10:20"); h1 = pd.Timestamp("2026-11-01 20:00")
    fut = cl.copy(); fut.loc[h1:] = 500.0
    assert CB.position_at(cl, T, None, 168, h1) == CB.position_at(fut, T, None, 168, h1) == -CB.SIZE
    assert CB.position_at(cl.loc[:h1 - pd.Timedelta(hours=1)], T, None, 168, h1) == -CB.SIZE


def test_position_at_matches_trade_pnl_holding():
    cl = _closes(jump_at=60) * (1 + 0.001 * np.sin(np.arange(300))); T = pd.Timestamp("2026-11-01 10:20")
    p = CB.trade_pnl(cl, pd.Series(dtype=float), T)
    held = [h for h in cl.index if CB.position_at(cl, T, None, CB.HOLD_H, h) != 0]
    assert held == list(p.index)


def test_cap_lowcap_total_over_all_event_sleeves():
    book = {"lowcap_sleeves": ["listing short", "venue listing short", "hodler short"],
            "by_sleeve_usd": {"AAA": {"listing short": -1.0}, "BBB": {"venue listing short": -1.0}, "CCC": {"hodler short": -1.0, "C*": 2.0},
                              "BTC": {"C*": 5.0}}}
    t = RV.cap_lowcap({"AAA": -9000.0, "BBB": -6000.0, "CCC": -4000.0, "BTC": 50000.0}, book, 10000.0, 9000.0)
    assert t["BTC"] == 50000.0
    assert abs(sum(abs(t[c]) for c in ("AAA", "BBB", "CCC")) - 9000.0) < 1e-6
    assert abs(t["AAA"] / t["BBB"] - 1.5) < 1e-9
    t = RV.cap_lowcap({"AAA": -20000.0}, book, 10000.0, 0.0); assert t["AAA"] == -10000.0
    assert RV.lowcap_coins({"by_sleeve_usd": {"X": {"listing short": -1.0}, "Y": {"venue listing short": -1.0}}}) == {"X"}   # old v9.8 books


def _fake_root(tmp: Path, h1="2026-11-02 08:00:00", stale_hodler=False) -> Path:
    r = tmp / "root"; ix = pd.date_range("2023-01-01", "2026-10-29 23:00", freq="h"); rng = np.random.default_rng(3)
    sl = ["C*", "trend 4h", "Weiss expiry", "listing short"]
    (r / "results/v99").mkdir(parents=True); (r / "config").mkdir(); (r / "paper_trading/v98").mkdir(parents=True)
    X = pd.DataFrame(rng.normal(0, 1e-3, (len(ix), 4)), index=ix, columns=sl); X["port"] = X.sum(axis=1); X.to_parquet(r / "results/v98_oct_oos.parquet")
    L = pd.DataFrame({"hour": pd.date_range("2026-10-30 00:00", "2026-11-02 07:00", freq="h")})
    for s in sl:
        L[s] = rng.normal(0, 1e-3, len(L))
    L.to_csv(r / "paper_trading/v98/ledger_hourly.csv", index=False)
    for name, (d, prefix) in VB.EVENT.items():
        ev = pd.Series(0.0, index=ix); ev.iloc[::200] = rng.normal(0, 5e-3, len(ev.iloc[::200])); ev.to_frame(name).to_parquet(r / prefix)
        (r / "paper_trading" / d).mkdir(parents=True)
        pd.DataFrame({"hour": pd.date_range("2026-11-01", "2026-11-02 07:00", freq="h"), name: 0.0, "port": 0.0}).to_csv(
            r / "paper_trading" / d / "ledger_hourly.csv", index=False)
        pos = {"NEWC": -0.05} if d == "venueshort" else ({"HOD": -0.05} if d == "hodlershort" else {})
        fh = "2026-11-02 07:00:00" if (stale_hodler and d == "hodlershort") else h1
        (r / "paper_trading" / d / "open_positions.json").write_text(json.dumps({"for_hour_utc": fh, "positions": pos}))
    (r / "config/paper_v98.json").write_text(json.dumps({"frozen": {"v98_scale": 0.9}}))
    book = {"for_hour_utc": h1, "made_at_utc": "2026-11-02 08:11:00", "equity": 200000.0, "risk": 2.0,
            "target_notional_usd": {"BTC": 30000.0, "LST": -2000.0},
            "by_sleeve_usd": {"BTC": {"C*": 20000.0, "trend 4h": 10000.0}, "LST": {"listing short": -2000.0}},
            "sleeve_multipliers": {"C*": 0.6, "trend 4h": 0.7, "Weiss expiry": 1.3, "listing short": 0.25}, "cascade_limit_orders": []}
    (r / "paper_trading/v98/book_next_hour.json").write_text(json.dumps(book))
    return r


def _hashes(r: Path):
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((r / "paper_trading/v98").rglob("*")) if p.is_file()}


def test_book_builder(tmp_path):
    r = _fake_root(tmp_path); before = _hashes(r)
    b = VB.build(root=r)
    assert _hashes(r) == before                                           # v9.8 paper files untouched
    assert (r / "paper_trading/v99cand/book_next_hour.json").exists()
    e = b["sleeve_multipliers"]; close = lambda a, x: abs(a / x - 1) < 2e-4            # e is rounded to 4 decimals in the book
    assert close(b["by_sleeve_usd"]["BTC"]["C*"], 20000.0 * e["C*"] / 0.6)
    assert close(b["by_sleeve_usd"]["LST"]["listing short"], -2000.0 * e["listing short"] / 0.25)
    assert close(b["by_sleeve_usd"]["NEWC"]["venue listing short"], -0.05 * e["venue listing short"] * 200000 * 2.0)
    assert set(b["lowcap_sleeves"]) >= {"listing short", "venue listing short", "futures-delisting short", "binance add short", "hodler short"}
    assert abs(b["target_notional_usd"]["BTC"] - sum(b["by_sleeve_usd"]["BTC"].values())) < 0.02
    assert b["made_at_utc"] == "2026-11-02 08:11:00" and "DRY-RUN" in b["note"]


def test_book_builder_stale_event_positions_are_flat(tmp_path):
    r = _fake_root(tmp_path, stale_hodler=True); b = VB.build(root=r, write=False)
    assert "HOD" not in b["target_notional_usd"] and b["event_positions_stale"] == ["hodler short"]
    assert "NEWC" in b["target_notional_usd"]


def test_runner_v99_dryrun_separate_state(tmp_path):
    r = _fake_root(tmp_path); b = VB.build(root=r); bp = r / "paper_trading/v99cand/book_next_hour.json"
    sd = tmp_path / "bot_state_v99cand"; now = pd.Timestamp("2026-11-02 08:15", tz="UTC")
    res = RV.one_pass(bp, "challenge", Rules(), sd, now=now)
    st = json.loads((sd / "state.json").read_text()); assert res["book"] == "v99cand" and res["orders"] >= 1
    lc = RV.lowcap_coins(b); assert "NEWC" in lc and "LST" in lc
    assert sum(abs(v) for c, v in st["positions"].items() if c in lc) <= Rules().lowcap_total_frac * 200000 + 1e-6
    assert RV.one_pass(bp, "challenge", Rules(), sd, now=now)["action"] == "no new book"
    with pytest.raises(SystemExit):
        RV.one_pass(bp, "challenge", Rules(), sd, adapter_name="bybit", now=now)
    assert not (tmp_path / "bot_state").exists()

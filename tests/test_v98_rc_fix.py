"""v9.8 approved bugfix 2026-11-02 (relative crowding 6): duplicate timestamps in the live ratio updater, missing / stale data
monitoring, the daily position transition at 00:00 UTC and the absence of look-ahead."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

from qpl.live import binance_public as BP  # noqa: E402


class _FakeClient:
    """pages that overlap differently per endpoint (one endpoint repeats timestamps across pages, the others do not): merging the
    columns then needs an index alignment, which raised 'cannot reindex on an axis with duplicate labels' on the PC"""
    def __init__(self, *a, **k):
        pass

    def get(self, url, params):
        t0 = int(params["startTime"]); step = 300_000
        base = pd.Timestamp("2026-10-27 00:00").value // 1_000_000
        if t0 <= base:
            ts = [base + i * step for i in range(500)]
        else:
            back = 3 if "globalLongShortAccountRatio" in url else 0       # this endpoint repeats its last 3 timestamps ...
            extra = 1 if "takerlongshortRatio" in url else 0               # ... and this one is one bar ahead of the others
            last = t0 - 1                                                  # the caller asks from last timestamp + 1 ms
            ts = [last + (1 - back) * step + i * step for i in range(10 + extra)]
        return [{"timestamp": t, "longShortRatio": 1.0 + i / 1e4, "longAccount": 0.5, "shortAccount": 0.5, "buySellRatio": 1.0,
                 "buyVol": 1.0, "sellVol": 1.0} for i, t in enumerate(ts)]


def test_update_ratios_survives_duplicate_timestamps(tmp_path, monkeypatch):
    monkeypatch.setattr(BP, "Client", _FakeClient)
    now = pd.Timestamp("2026-10-28 18:00")
    n = BP.update_ratios(tmp_path, ["BTC"], now=now, log=lambda *a: None)          # raised 'cannot reindex ... duplicate labels' before the fix
    d = pd.read_parquet(tmp_path / "BTCUSDT_ratios.parquet")
    assert n > 0 and not d.index.duplicated().any() and d.index.is_monotonic_increasing


def test_ratio_status_flags_missing_and_stale(tmp_path):
    now = pd.Timestamp("2026-11-02 08:00")
    pd.DataFrame({"x": [1.0, 2.0]}, index=pd.DatetimeIndex(["2026-11-02 07:00", "2026-11-02 07:30"])).to_parquet(tmp_path / "BTCUSDT_ratios.parquet")
    pd.DataFrame({"x": [1.0]}, index=pd.DatetimeIndex(["2026-11-02 02:00"])).to_parquet(tmp_path / "ETHUSDT_ratios.parquet")
    st = BP.ratio_status(tmp_path, ["BTC", "ETH", "SOL"], now)
    assert st["BTC"]["stale"] is False and st["BTC"]["age_h"] == 0.5
    assert st["ETH"]["stale"] is True and st["SOL"] == {"last": None, "age_h": None, "duplicates": 0, "stale": True}


@pytest.fixture()
def BL(monkeypatch):
    import basket_live as BLmod
    return BLmod


def _rw(days):
    """synthetic weights: each daily row d gets value d.day / 100 for every coin (distinct per day); the 8-hour frame is constant"""
    w = pd.DataFrame({c: [d.day / 100 for d in days] for c in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE")}, index=days)
    h8 = pd.DataFrame(0.0, index=pd.date_range(days[0], days[-1] + pd.Timedelta(hours=16), freq="8h"), columns=w.columns)
    return {"daily": {"a": w, "b": w}, "smooth": {"a": w, "b": w}, "h8": {"a": h8, "b": h8}}


def test_daily_transition_at_midnight_is_continuous(BL, monkeypatch):
    full = pd.date_range("2026-10-01", "2026-10-21")
    short = full[:-1]                                                  # END = 23:00 on 10-20: the calendar stops at 10-20
    RW = _rw(full)
    h = pd.DatetimeIndex(["2026-10-20 23:00", "2026-10-21 00:00", "2026-10-21 01:00"])
    monkeypatch.setattr(BL, "DAYS", full); ref = BL.rc_positions(h, RW)
    monkeypatch.setattr(BL, "DAYS", short); got = BL.rc_positions(h[:2], RW)
    assert np.allclose(got.to_numpy(), ref.iloc[:2].to_numpy())              # before the fix the 00:00 row was 0 for 4 of 6 versions
    # the transition uses the row decided at the previous close: 10-21 00:00 holds row 10-20 (value 0.20 x 4/6), not row 10-21
    assert np.allclose(got.loc["2026-10-21 00:00"].to_numpy(), 0.20 * 4 / 6)
    assert np.allclose(got.loc["2026-10-20 23:00"].to_numpy(), 0.19 * 4 / 6)


def test_no_lookahead_future_rows_do_not_change_positions(BL, monkeypatch):
    days = pd.date_range("2026-10-01", "2026-10-21"); RW = _rw(days)
    monkeypatch.setattr(BL, "DAYS", days[:-1])
    h = pd.DatetimeIndex(["2026-10-21 00:00"])
    a = BL.rc_positions(h, RW)
    RW2 = _rw(days)
    for k in ("daily", "smooth"):
        for w in RW2[k].values():
            w.loc["2026-10-21"] = 9.99                                  # a value only known at the close of 10-21
    b = BL.rc_positions(h, RW2)
    assert np.allclose(a.to_numpy(), b.to_numpy())


def test_missing_daily_input_keeps_original_rule(BL, monkeypatch):
    """the fix does not change the strategy's own handling of missing data: a NaN weight row stays a 0 position for that day"""
    days = pd.date_range("2026-10-01", "2026-10-21"); RW = _rw(days)
    for k in ("daily", "smooth"):
        for w in RW[k].values():
            w.loc["2026-10-19"] = np.nan
    monkeypatch.setattr(BL, "DAYS", days)
    p = BL.rc_positions(pd.DatetimeIndex(["2026-10-20 12:00"]), RW)
    assert np.allclose(p.to_numpy(), 0.0)


def test_calendar_unchanged_inside_research_range(BL):
    assert BL._days_for(pd.DatetimeIndex([BL.DAYS[-1]])).equals(BL.DAYS)
    nxt = BL._days_for(pd.DatetimeIndex([BL.DAYS[-1] + pd.Timedelta(hours=24)]))
    assert len(nxt) == len(BL.DAYS) + 1 and nxt[:-1].equals(BL.DAYS)

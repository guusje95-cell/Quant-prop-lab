import numpy as np
import pandas as pd
import pytest

from qpl.backtesting import vector as V


def bars(prices):
    idx = pd.date_range("2024-01-01", periods=len(prices), freq="1h", tz="UTC")
    p = np.asarray(prices, float)
    return pd.DataFrame({"open": p, "high": p, "low": p, "close": p}, index=idx)


def test_position_earns_next_open_to_open_only():
    b = bars([100, 100, 110, 121, 121])
    w = pd.Series([1.0, 0, 0, 0, 0], index=b.index)       # decided at close of bar 0
    r = V.run(b, w, cost_bps=0)
    # filled at open[1]=100, held to open[2]=110 -> +10%
    assert r.gross.iloc[0] == pytest.approx(0.10) and r.gross.iloc[1:].sum() == 0


def test_costs_on_turnover():
    b = bars([100] * 5)
    w = pd.Series([1.0, 1.0, -1.0, 0, 0], index=b.index)
    r = V.run(b, w, cost_bps=10)
    assert r.cost.sum() == pytest.approx((1 + 2 + 1) * 10 / 1e4)


def test_funding_sign_and_timing():
    b = bars([100] * 6)
    w = pd.Series([1.0, 1.0, 0, 0, 0, 0], index=b.index)   # long held over [open1, open3)
    f = pd.Series([0.001, 0.001], index=pd.DatetimeIndex(["2024-01-01 01:30", "2024-01-01 04:30"], tz="UTC"))
    r = V.run(b, w, cost_bps=0, funding=f)
    # first settlement (01:30) falls in the long's holding interval -> long pays; second (04:30) when flat
    assert r.funding.sum() == pytest.approx(-0.001)


def test_signal_shift_leakage_guard():
    # a strategy that 'knows' the next return must not profit if it only uses close[t]
    rng = np.random.default_rng(0)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 2000)))
    b = bars(p)
    w = np.sign(b.close.pct_change()).fillna(0)          # uses info up to close t only
    r = V.run(b, w, cost_bps=0)
    assert abs(r.gross.mean()) < 3 * r.gross.std() / np.sqrt(len(r))


def test_funding_with_mixed_datetime_units():
    # regression V4-B1: bars in microseconds, funding grid in nanoseconds
    b = bars([100] * 6)
    b.index = b.index.as_unit("us")
    w = pd.Series([1.0, 1.0, 0, 0, 0, 0], index=b.index)
    f = pd.Series([0.001], index=pd.DatetimeIndex(["2024-01-01 01:30"], tz="UTC").as_unit("ns"))
    r = V.run(b, w, cost_bps=0, funding=f)
    assert r.funding.sum() == pytest.approx(-0.001)


def test_daily_realized_labels_pnl_where_earned():
    # regression V4-C1: w decided at the 23:00 (day 1) bar close is filled at 00:00 day 2 and earns 00:00 -> 01:00 day 2
    idx = pd.date_range("2024-01-01 22:00", periods=5, freq="1h", tz="UTC")
    b = pd.DataFrame({"open": [100, 100, 100, 110, 110.0]}, index=idx)
    b["high"] = b["low"] = b["close"] = b["open"]
    w = pd.Series([0, 1.0, 0, 0, 0], index=idx)
    r = V.run(b, w, cost_bps=0)
    assert r.gross.sum() == pytest.approx(0.10)
    assert V.daily(r)["gross"].loc["2024-01-01"] == pytest.approx(0.10)              # legacy decision-time label
    assert V.daily(r, at="realized")["gross"].loc["2024-01-02"] == pytest.approx(0.10)  # earned on day 2

import numpy as np
import pandas as pd
import pytest

from qpl.htf import core as H


def bars(n=24 * 80, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-06 00:00", periods=n, freq="1h", tz="UTC")
    c = 100 + np.cumsum(rng.normal(0, 0.3, n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.uniform(0, 0.3, n)
    l = np.minimum(o, c) - rng.uniform(0, 0.3, n)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=idx)


def test_levels_use_completed_periods_only():
    df = bars()
    a = H.htf_frame(df, "crypto")
    df2 = df.copy(); df2.iloc[1500:, :] += 50          # change the future
    b = H.htf_frame(df2, "crypto")
    # levels/ATR for bars before the change are identical; levels inside the changed DAY must not move
    first_changed_day = a.day.iloc[1500]
    m = a.day < first_changed_day
    pd.testing.assert_frame_equal(a[m], b[m])
    same_day = a.day == first_changed_day
    pd.testing.assert_series_equal(a.loc[same_day, "pdh"], b.loc[same_day, "pdh"])


def test_events_no_lookahead():
    df = bars(seed=2)
    lv = H.htf_frame(df, "crypto")
    e1 = [(e.i, e.direction, e.strategy) for e in H.detect_events(df, lv, "PD") if e.i < 1400]
    df2 = df.copy(); df2.iloc[1410:, :] *= 1.2
    lv2 = H.htf_frame(df2, "crypto")
    e2 = [(e.i, e.direction, e.strategy) for e in H.detect_events(df2, lv2, "PD") if e.i < 1400]
    assert e1 == e2


def test_stop_checked_before_target_and_gap_fill():
    idx = pd.date_range("2020-01-01", periods=6, freq="1h", tz="UTC")
    df = pd.DataFrame({"open": [10, 10, 10, 10, 10, 10.0], "high": [10, 10, 13, 10, 10, 10.0],
                       "low": [10, 10, 8, 10, 10, 10.0], "close": [10] * 6}, index=idx)
    ev = [H.Event(0, +1, 9.0, "A1_SR1", "PD", 10.0)]          # long, stop 9, target 1.5R = 11.5; bar 2 hits both
    t = H.simulate(df, ev, lambda p: 0.0, hold=4, target_r=1.5)
    assert t.iloc[0].why == "stop" and t.iloc[0].R_gross == pytest.approx(-1.0)
    df.loc[idx[2], ["open", "low"]] = [8.5, 8.0]               # gap below stop -> fill at open 8.5
    t = H.simulate(df, ev, lambda p: 0.0, hold=4)
    assert t.iloc[0].exit == pytest.approx(8.5) and t.iloc[0].R_gross == pytest.approx(-1.5)


def test_entry_is_next_open_and_costs_in_R():
    idx = pd.date_range("2020-01-01", periods=10, freq="1h", tz="UTC")
    o = np.arange(10, 20, dtype=float)
    df = pd.DataFrame({"open": o, "high": o + 0.5, "low": o - 0.5, "close": o}, index=idx)
    t = H.simulate(df, [H.Event(2, +1, 11.0, "A1_SR1", "PD", 0.0)], lambda p: 0.2, hold=3)
    r = t.iloc[0]
    assert r.entry == 13.0 and r.exit == 16.0 and r.R_net == pytest.approx((3 - 0.2) / 2.0)


def test_daily_mtm_sums_to_trade_R():
    df = bars(24 * 80, seed=9)
    lv = H.htf_frame(df, "crypto")
    ev = [e for e in H.detect_events(df, lv, "PD")]
    cf = lambda p: 0.05
    t = H.simulate(df, ev, cf, hold=6)
    assert len(t) > 5
    m = H.daily_mtm(df, t, cf)
    assert m.sum() == pytest.approx(t.R_net.sum(), rel=1e-9)

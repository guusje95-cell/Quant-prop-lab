import numpy as np
import pandas as pd
import pytest

from qpl.backtesting import engine as E


def bars(rows):
    idx = pd.date_range("2024-01-02 14:30", periods=len(rows), freq="15min", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def test_market_order_fills_next_open_with_slippage_never_same_bar():
    df = bars([(100, 101, 99, 100), (102, 103, 101, 102), (102, 104, 101, 103)])
    o = E.Orders(3)
    o.entry_dir[0] = 1; o.entry_type[0] = E.MARKET
    o.flat_bar[2] = True
    tr = E.run(df, o, np.zeros(3), tick=0.25, slip_ticks=1)
    assert len(tr) == 1
    assert tr.entry_i[0] == 1 and tr.entry_px[0] == pytest.approx(102.25)
    assert tr.exit_px[0] == pytest.approx(103 - 0.25)
    assert tr.reason[0] == E.EX_FLAT


def test_stop_and_target_same_bar_assumes_stop_first():
    df = bars([(100, 100, 100, 100), (100, 100.5, 99.5, 100), (100, 105, 95, 100)])
    o = E.Orders(3)
    o.entry_dir[0] = 1; o.entry_type[0] = E.MARKET
    o.stop_dist[0] = 2.0; o.tgt_dist[0] = 2.0
    tr = E.run(df, o, np.zeros(3), tick=0.25, slip_ticks=0)
    assert tr.reason[0] == E.EX_STOP
    assert tr.exit_px[0] == pytest.approx(98.0)


def test_gap_through_stop_fills_at_open_not_stop():
    df = bars([(100, 100, 100, 100), (100, 100.5, 99.5, 100), (95, 96, 94, 95)])
    o = E.Orders(3)
    o.entry_dir[0] = 1; o.entry_type[0] = E.MARKET; o.stop_dist[0] = 2.0
    tr = E.run(df, o, np.zeros(3), tick=0.25, slip_ticks=1)
    assert tr.exit_px[0] == pytest.approx(95 - 0.25)


def test_limit_requires_trade_through():
    df = bars([(100, 100, 100, 100), (100, 100.5, 99.0, 100), (100, 100.5, 98.75, 100)])
    o = E.Orders(3)
    o.entry_dir[0] = 1; o.entry_type[0] = E.LIMIT; o.entry_px[0] = 99.0; o.entry_expiry[0] = 2
    tr = E.run(df, o, np.zeros(3), tick=0.25, slip_ticks=1)
    # bar1 low touches 99.0 exactly -> no fill; bar2 trades through -> fill at 99.0, no slippage
    assert tr.entry_i[0] == 2 and tr.entry_px[0] == pytest.approx(99.0)


def test_target_needs_trade_through_and_has_no_slippage():
    df = bars([(100, 100, 100, 100), (100, 102.0, 99.9, 101), (101, 102.25, 100.5, 101)])
    o = E.Orders(3)
    o.entry_dir[0] = 1; o.entry_type[0] = E.MARKET; o.tgt_dist[0] = 2.0
    tr = E.run(df, o, np.zeros(3), tick=0.25, slip_ticks=0)
    assert tr.exit_i[0] == 2 and tr.exit_px[0] == pytest.approx(102.0) and tr.reason[0] == E.EX_TARGET


def test_stop_entry_and_stop_in_same_bar_counts_loss():
    df = bars([(100, 100, 100, 100), (100, 102, 97, 101)])
    o = E.Orders(2)
    o.entry_dir[0] = 1; o.entry_type[0] = E.STOP; o.entry_px[0] = 101; o.stop_px[0] = 98; o.entry_expiry[0] = 1
    tr = E.run(df, o, np.zeros(2), tick=0.25, slip_ticks=0)
    assert tr.reason[0] == E.EX_STOP and tr.pnl_pts[0] == pytest.approx(-3.0)


def test_pending_stop_cancelled_at_session_change():
    df = bars([(100, 100, 100, 100), (100, 100.5, 99.5, 100), (100, 110, 99, 105)])
    o = E.Orders(3)
    o.entry_dir[1] = 1; o.entry_type[1] = E.STOP; o.entry_px[1] = 101; o.entry_expiry[1] = 5
    sess = np.array([0, 0, 1])
    tr = E.run(df, o, sess, tick=0.25, slip_ticks=0)
    assert len(tr) == 0


def test_oco_bracket_picks_triggered_side_and_opposite_stop():
    df = bars([(100, 100, 100, 100), (100, 100.5, 97.5, 98), (98, 98.5, 96, 97)])
    o = E.Orders(3)
    o.entry_dir[0] = 2; o.entry_type[0] = E.STOP; o.entry_px[0] = 101; o.entry_px2[0] = 98; o.entry_expiry[0] = 2
    o.flat_bar[2] = True
    tr = E.run(df, o, np.zeros(3), tick=0.25, slip_ticks=0)
    assert tr.dir[0] == -1 and tr.entry_px[0] == pytest.approx(98.0)
    assert tr.stop0[0] == pytest.approx(101.0)


def test_trailing_stop_uses_completed_bars_only():
    df = bars([(100, 100, 100, 100), (100, 105, 99.5, 104), (104, 104.5, 102.5, 103)])
    o = E.Orders(3)
    o.entry_dir[0] = 1; o.entry_type[0] = E.MARKET; o.trail_dist[0] = 2.0
    tr = E.run(df, o, np.zeros(3), tick=0.25, slip_ticks=0)
    # after bar1 completes, trail = 105-2 = 103; bar2 low 102.5 hits it
    assert tr.exit_i[0] == 2 and tr.exit_px[0] == pytest.approx(103.0)


def test_mae_is_recorded():
    df = bars([(100, 100, 100, 100), (100, 101, 97, 100), (100, 102, 99, 101)])
    o = E.Orders(3)
    o.entry_dir[0] = 1; o.entry_type[0] = E.MARKET; o.flat_bar[2] = True
    tr = E.run(df, o, np.zeros(3), tick=0.25, slip_ticks=0)
    assert tr.mae_pts[0] == pytest.approx(-3.0) and tr.mfe_pts[0] == pytest.approx(2.0)


def test_signal_exit_next_open():
    df = bars([(100, 100, 100, 100), (100, 101, 99, 100), (101, 102, 100, 101), (103, 104, 102, 103)])
    o = E.Orders(4)
    o.entry_dir[0] = 1; o.entry_type[0] = E.MARKET; o.exit_sig[2] = 2
    tr = E.run(df, o, np.zeros(4), tick=0.25, slip_ticks=0)
    assert tr.exit_i[0] == 3 and tr.exit_px[0] == pytest.approx(103.0) and tr.reason[0] == E.EX_SIGNAL


def test_max_trades_per_session():
    df = bars([(100, 101, 99, 100)] * 8)
    o = E.Orders(8)
    o.entry_dir[:] = 1; o.entry_type[:] = E.MARKET; o.exit_sig[:] = 2
    o.max_trades_sess = 2
    tr = E.run(df, o, np.zeros(8), tick=0.25, slip_ticks=0)
    assert len(tr) == 2


def test_directional_exit_signal_only_applies_to_matching_side():
    df = bars([(100, 100, 100, 100), (100, 101, 99, 100), (101, 102, 100, 101), (103, 104, 102, 103)])
    o = E.Orders(4)
    o.entry_dir[0] = 1; o.entry_type[0] = E.MARKET; o.exit_sig[1] = -1; o.exit_sig[2] = 1
    tr = E.run(df, o, np.zeros(4), tick=0.25, slip_ticks=0)
    assert tr.exit_i[0] == 3

"""Look-ahead / leakage tests on REAL data: orders generated at bar t must not change when
all data after bar t is deleted (and the context is rebuilt from the truncated raw data)."""
import numpy as np
import pytest

from qpl.data import loaders
from qpl.strategies import index_intraday as SI
from qpl.strategies import v3_intraday  # noqa: F401  (registers v3 strategies)

NAN = float("nan")
CASES = [
    ("orb", dict(or_bars=2, mode="candle_mkt")),
    ("orb", dict(or_bars=2, mode="bracket")),
    ("intraday_momentum", dict(thr_sd=0.25, use_r12=True)),
    ("noise_area", dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)),
    ("overnight_drift", dict(entry_min=1140, exit_min=180, stop_atr=1.0)),
    ("gap_fade", dict()),
    ("failed_breakout", dict(back_bars=2)),
    ("extreme_reversion", dict(k=2.5, hold_bars=4)),
    ("compression_breakout", dict(or_bars=2, range_ratio_max=0.8)),
    ("turn_of_month", dict()),
    ("noise_pullback", dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)),
    ("gap_continuation", dict()),
    ("asian_breakout", dict()),
    ("asian_reversion", dict()),
]
FIELDS = ["entry_dir", "entry_type", "entry_px", "entry_px2", "stop_px", "stop_dist", "tgt_dist", "trail_dist",
          "exit_sig", "risk_ref"]


@pytest.fixture(scope="module")
def raw():
    df = loaders.load("dukascopy", "US100", "M15")
    return df.loc["2016-01-01":"2016-09-30"]


@pytest.mark.parametrize("name,prm", CASES)
def test_orders_invariant_to_future_data(raw, name, prm):
    full_ctx = SI.build_context(raw, 15)
    full = SI.STRATEGIES[name](full_ctx, prm)
    rng = np.random.default_rng(0)
    n = len(raw)
    for T in rng.integers(n // 2, n - 10, size=4):
        ctx_t = SI.build_context(raw.iloc[:T], 15)
        tr = SI.STRATEGIES[name](ctx_t, prm)
        for f in FIELDS:
            a = getattr(full, f)[: T - 1]
            b = getattr(tr, f)[: T - 1]
            assert np.array_equal(np.nan_to_num(a, nan=-9e9), np.nan_to_num(b, nan=-9e9)), (name, f, T)


def test_engine_trades_invariant_to_future_data(raw):
    """Trades fully closed before T must be identical with and without data after T."""
    from qpl.backtesting import engine as E
    prm = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
    ctx = SI.build_context(raw, 15)
    tr_full = E.run(ctx, SI.noise_area(ctx, prm), SI.rth_session(ctx), 0.25, 0)
    T = int(len(raw) * 0.7)
    ctx_t = SI.build_context(raw.iloc[:T], 15)
    tr_t = E.run(ctx_t, SI.noise_area(ctx_t, prm), SI.rth_session(ctx_t), 0.25, 0)
    a = tr_full[tr_full.exit_i < T - 2].reset_index(drop=True)
    b = tr_t[tr_t.exit_i < T - 2].reset_index(drop=True)
    assert len(a) == len(b) and np.allclose(a.pnl_pts, b.pnl_pts)


def test_future_price_shock_does_not_change_past_signals(raw):
    """Multiply all prices after T by 1.5: signals before T must be unchanged."""
    prm = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
    T = int(len(raw) * 0.6)
    shocked = raw.copy()
    shocked.iloc[T:, :4] *= 1.5
    a = SI.noise_area(SI.build_context(raw, 15), prm)
    b = SI.noise_area(SI.build_context(shocked, 15), prm)
    assert np.array_equal(a.entry_dir[: T - 1], b.entry_dir[: T - 1])
    assert np.array_equal(a.exit_sig[: T - 1], b.exit_sig[: T - 1])

import numpy as np
import pandas as pd

from qpl.strategies import cft_e2 as E


def _px(seed=0, n=400):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.DataFrame({"BTC": 100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, n))),
                         "ETH": 50 * np.exp(np.cumsum(rng.normal(0.0, 0.04, n)))}, index=idx)


def test_no_lookahead_and_long_only():
    c = _px()
    w_full = E.raw_weights(c)
    w_cut = E.raw_weights(c.iloc[:300])
    pd.testing.assert_frame_equal(w_full.iloc[:300], w_cut)
    assert (w_full >= 0).all().all() and (w_full.sum(axis=1) <= 1.0 + 1e-12).all()


def test_warmup_flat():
    w = E.raw_weights(_px())
    assert (w.iloc[:199] == 0).all().all()

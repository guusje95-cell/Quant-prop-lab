import numpy as np
import pandas as pd
import pytest

from qpl.backtesting import panel as PB
from qpl.strategies import futures_factors as FF


def synth(T=1600, K=8, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-03", periods=T, freq="B")
    r = pd.DataFrame(rng.normal(0, 0.01, (T, K)), index=idx, columns=[f"I{k}" for k in range(K)])
    r.iloc[:300, 0] = np.nan                                  # late starter
    carry = pd.DataFrame(rng.normal(0, 0.05, (T, K)), index=idx, columns=r.columns)
    classes = pd.Series(["A"] * 4 + ["B"] * 4, index=r.columns)
    return r, carry, classes


SIGS = {
    "tsmom": lambda r, c, k: FF.tsmom(r),
    "ct1": lambda r, c, k: FF.ct1_transfer(r),
    "ewmac": lambda r, c, k: FF.ewmac(r),
    "carry": lambda r, c, k: FF.carry(r, c),
    "xsmom": lambda r, c, k: FF.xs_momentum(r, k),
    "xsval": lambda r, c, k: FF.xs_value(r, k),
    "xsskew": lambda r, c, k: FF.xs_skew(r, k),
}


@pytest.mark.parametrize("name", list(SIGS))
def test_signals_have_no_lookahead(name):
    r, c, k = synth()
    a = SIGS[name](r, c, k)
    r2, c2 = r.copy(), c.copy()
    r2.iloc[1300:] = r2.iloc[1300:] * -3 + 0.02            # change the future only
    c2.iloc[1300:] = -c2.iloc[1300:]
    b = SIGS[name](r2, c2, k)
    pd.testing.assert_frame_equal(a.iloc[:1300], b.iloc[:1300])


def test_engine_lag_two_days():
    idx = pd.date_range("2000-01-03", periods=400, freq="B")
    r = pd.DataFrame({"X": np.full(400, 0.001)}, index=idx)
    r.iloc[350, 0] = 0.05
    s = pd.DataFrame({"X": np.zeros(400)}, index=idx)
    s.iloc[348, 0] = 1.0                                    # decided at close of 348 -> held over day 350
    out = PB.run(r, s, book_target=0.10)
    assert out.gross.iloc[350] > 0 and out.gross.iloc[349] == 0 and out.gross.iloc[351] == 0
    s2 = s.copy(); s2.iloc[348, 0] = 0; s2.iloc[349, 0] = 1.0   # decided at 349 -> held over day 351: misses the jump
    assert PB.run(r, s2, book_target=0.10).gross.iloc[350] == 0


def test_oracle_signal_cannot_profit_without_lookahead():
    r, _, _ = synth(seed=3)
    s = np.sign(r)                                          # sign of today's return, known at close t
    out = PB.run(r, s)
    x = out.gross.iloc[400:]
    assert abs(x.mean()) < 3 * x.std() / np.sqrt(len(x))


def test_costs_charged_on_turnover():
    r, _, _ = synth(seed=4)
    s = FF.tsmom(r, (21,))
    cost = pd.DataFrame(0.001, index=r.index, columns=r.columns)
    a = PB.run(r, s, cost)
    assert (a.cost >= 0).all() and a.cost.sum() > 0 and np.allclose(a.net, a.gross - a.cost)

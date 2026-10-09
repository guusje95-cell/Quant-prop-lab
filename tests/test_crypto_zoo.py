import numpy as np
import pandas as pd
import pytest

from qpl.strategies import crypto_zoo as Z


def frame(n=900, seed=0):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    o = np.r_[c[0], c[:-1]]; h = np.maximum(o, c) * 1.01; l = np.minimum(o, c) * 0.99
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=pd.date_range("2018-01-01", periods=n, freq="D"))


FUNCS = {
    "sma": lambda d: Z.sma_cross(d.close, 20, 100), "ema": lambda d: Z.ema_cross(d.close, 12, 26), "above": lambda d: Z.price_above_sma(d.close, 50),
    "tsmom": lambda d: Z.tsmom(d.close, 30), "donch": lambda d: Z.donchian_close(d.close, 20), "bb": lambda d: Z.boll_breakout(d.close, 20, 2),
    "bbr": lambda d: Z.boll_reversion(d.close, 20, 2), "rsi": lambda d: Z.rsi_reversion(d.close, 14, 30, 70), "rsi2": lambda d: Z.rsi_reversion(d.close, 2, 10, 90),
    "rsim": lambda d: Z.rsi_momentum(d.close, 14, 55, 45), "macd": lambda d: Z.macd(d.close, 12, 26, 9), "z": lambda d: Z.zscore_reversion(d.close, 5, 1.5),
    "sb": lambda d: Z.short_breakout(d.close, 7, 2), "vm": lambda d: Z.vol_managed_long(d.close, 30), "st": lambda d: Z.supertrend(d, 10, 3.0),
    "ichi": lambda d: Z.ichimoku(d, 9, 26, 52), "ha": lambda d: Z.heikin_ashi(d, 3),
}


@pytest.mark.parametrize("name", list(FUNCS))
def test_zoo_no_lookahead(name):
    d = frame()
    a = FUNCS[name](d)
    d2 = d.copy(); d2.iloc[700:] = d2.iloc[700:] * 1.7
    b = FUNCS[name](d2)
    pd.testing.assert_series_equal(a.iloc[:700], b.iloc[:700], check_names=False)
    assert a.abs().max() <= 1.0 + 1e-12

"""Example user strategy (a copy of _template.py, so you can see how plug-ins appear in the app). Delete or edit freely."""
import numpy as np
import pandas as pd

from qpl.lab.strategies import Param, Strategy, bars_per_day, per_asset


class MyBreakoutExample(Strategy):
    name = "My example: N-day high breakout"
    description = "Long when the close makes a new N-day high, stay long for H days. An example to copy."
    params = {"n": Param(20, 5, 120, 1, "lookback, days"), "hold": Param(5, 1, 30, 1, "holding period, days")}
    long_only = True

    def signal(self, bars, p):
        m = bars_per_day(bars)                       # 24 on hourly bars, 6 on 4h, 1 on daily
        n, h = int(p["n"] * m), int(p["hold"] * m)

        def one(c: pd.Series) -> pd.Series:
            trig = (c > c.rolling(n).max().shift(1)).astype(float)
            return trig.replace(0, np.nan).ffill(limit=max(0, h - 1)).fillna(0)
        return per_asset(bars, one)

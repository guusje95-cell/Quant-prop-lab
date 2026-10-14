"""Strategy plug-in system for the Backtest Lab.

A strategy is a class with a `name`, a `description`, a `params` dict of `Param`s and a `signal(bars, p)` method that
returns a DataFrame (same index/columns as bars.close) of target positions in [-1, 1] per asset (up to +-2 allowed
for conviction scaling), known at the CLOSE of
each bar (the engine trades them on the next bar, so a signal may use data up to and including its own bar).
The engine then sizes them (per-asset volatility scaling, equal weight across assets, leverage).

Add your own: drop a .py file into the `strategies_user/` folder at the repo root that defines one or more subclasses of
`Strategy` (see strategies_user/_template.py). They appear in the app automatically."""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
USER_DIR = ROOT / "strategies_user"


from qpl.lab.strategy_base import Param, Strategy  # noqa: E402,F401  (re-exported for plug-ins)


# ------------------------------------------------------------------ helpers (no look-ahead: only data up to t)
def short_breakout(c, n, hold):
    trig = pd.Series(np.where(c > c.rolling(n).max().shift(1), 1.0, np.where(c < c.rolling(n).min().shift(1), -1.0, 0.0)), index=c.index)
    return trig if hold <= 1 else trig.replace(0, np.nan).ffill(limit=hold - 1).fillna(0)


def tsmom(c, n):
    return np.sign(np.log(c).diff(n)).fillna(0)


def per_asset(bars, fn):
    return pd.DataFrame({s: fn(bars.close[s].dropna()) for s in bars.symbols}).reindex(bars.close.index).fillna(0)


def bars_per_day(bars):
    from qpl.lab.data import BPD
    return BPD.get(bars.freq, 1)


# ------------------------------------------------------------------ built-in strategies
class CStarTrend(Strategy):
    name = "C* trend + breakout (E2)"
    description = ("The research project's frozen crypto edge: average of 15 short breakout rules (5-20 day high, hold 1-3 days) "
                   "and 4 time-series momentum rules (14-90 days), long-only. Optional stablecoin-liquidity filter (O3): "
                   "x1.25 when USDT+USDC supply grew over 30 days, x0.75 when it shrank. Lookbacks are in days and scale "
                   "automatically on hourly / 4h bars.")
    params = {"stablecoin_filter": Param(True, help="needs stablecoin data (built in, or `download stablecoins`)"),
              "long_only": Param(True, help="research version is long-only")}
    BO = [(n, k) for n in (5, 7, 10, 14, 20) for k in (1, 2, 3)]
    TM = (14, 30, 60, 90)

    def signal(self, bars, p):
        m = bars_per_day(bars)

        def one(c):
            bo = sum(short_breakout(c, n * m, k * m) for n, k in self.BO) / len(self.BO)
            tm = sum(tsmom(c, n * m) for n in self.TM) / len(self.TM)
            return (0.5 * bo.clip(lower=0) + 0.5 * tm.clip(lower=0)) if p["long_only"] else 0.5 * bo + 0.5 * tm
        s = per_asset(bars, one)
        if p["stablecoin_filter"]:
            from qpl.lab.data import stablecoin_caps
            caps = stablecoin_caps()
            if caps is not None:
                day = s.index.floor("D")
                g = np.log(caps.where(caps > 0)).diff(30)
                f = pd.Series(np.where(g > 0, 1.25, np.where(g <= 0, 0.75, 1.0)), index=g.index).shift(1)   # 1-day publication lag
                s = s.mul(f.reindex(day).fillna(1.0).to_numpy(), axis=0)
        return s


class BuyHold(Strategy):
    name = "Buy & hold (benchmark)"
    description = "Always long every asset (equal risk). Use it as the benchmark: an edge has to beat this."
    params = {}

    def signal(self, bars, p):
        return pd.DataFrame(1.0, index=bars.close.index, columns=bars.symbols).where(bars.close.notna(), 0.0)


class SMACross(Strategy):
    name = "Moving-average crossover"
    description = "Long when the fast moving average is above the slow one; short (or flat if long-only) otherwise."
    params = {"fast": Param(20, 2, 200, 1, "days"), "slow": Param(100, 5, 400, 1, "days"), "long_only": Param(False)}

    def signal(self, bars, p):
        m = bars_per_day(bars); f, s = int(p["fast"] * m), int(p["slow"] * m)
        out = per_asset(bars, lambda c: np.sign(c.rolling(f).mean() - c.rolling(s).mean()).fillna(0))
        return out.clip(lower=0) if p["long_only"] else out


class Donchian(Strategy):
    name = "Donchian channel breakout (turtle)"
    description = "Enter long on a close above the n-day high (short below the n-day low), exit on the opposite n/2-day channel."
    params = {"n": Param(20, 5, 200, 1, "entry channel, days"), "long_only": Param(False)}

    def signal(self, bars, p):
        m = bars_per_day(bars); n = int(p["n"] * m); x = max(2, n // 2)

        def one(c):
            hi, lo = c.rolling(n).max().shift(1), c.rolling(n).min().shift(1)
            xhi, xlo = c.rolling(x).max().shift(1), c.rolling(x).min().shift(1)
            out = np.zeros(len(c)); cur = 0.0
            el, es, xl, xs = (c > hi).to_numpy(), (c < lo).to_numpy(), (c < xlo).to_numpy(), (c > xhi).to_numpy()
            for t in range(len(c)):
                if cur == 0:
                    cur = 1.0 if el[t] else (-1.0 if es[t] else 0.0)
                elif cur == 1 and (xl[t] or es[t]):
                    cur = -1.0 if es[t] else 0.0
                elif cur == -1 and (xs[t] or el[t]):
                    cur = 1.0 if el[t] else 0.0
                out[t] = cur
            return pd.Series(out, index=c.index)
        s = per_asset(bars, one)
        return s.clip(lower=0) if p["long_only"] else s


class TSMOM(Strategy):
    name = "Time-series momentum"
    description = "Long if the asset rose over the lookback, short (or flat) if it fell."
    params = {"lookback": Param(30, 2, 365, 1, "days"), "long_only": Param(False)}

    def signal(self, bars, p):
        n = int(p["lookback"] * bars_per_day(bars))
        s = per_asset(bars, lambda c: tsmom(c, n))
        return s.clip(lower=0) if p["long_only"] else s


class RSIReversion(Strategy):
    name = "RSI mean reversion"
    description = "Buy when RSI is oversold, sell when overbought, exit at RSI 50. (In the research this lost money on crypto.)"
    params = {"n": Param(14, 2, 50, 1, "RSI length, bars"), "lo": Param(30, 5, 45, 1), "hi": Param(70, 55, 95, 1), "long_only": Param(False)}

    def signal(self, bars, p):
        n, lo, hi = int(p["n"]), p["lo"], p["hi"]

        def one(c):
            d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, min_periods=n).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, min_periods=n).mean()
            r = (100 - 100 / (1 + up / dn.replace(0, np.nan))).to_numpy()
            out = np.zeros(len(c)); cur = 0.0
            for t in range(len(c)):
                v = r[t]
                if np.isnan(v):
                    out[t] = cur; continue
                if cur == 0:
                    cur = 1.0 if v < lo else (-1.0 if v > hi else 0.0)
                elif cur == 1 and v > 50:
                    cur = 0.0
                elif cur == -1 and v < 50:
                    cur = 0.0
                out[t] = cur
            return pd.Series(out, index=c.index)
        s = per_asset(bars, one)
        return s.clip(lower=0) if p["long_only"] else s


BUILTIN = [CStarTrend, BuyHold, SMACross, Donchian, TSMOM, RSIReversion]


def _paper_strategies():
    from qpl.lab.strategies_papers import IntradayMomentumGao, KalmanPairs, MaxAIQLearning, NoiseAreaMomentum
    return [KalmanPairs, MaxAIQLearning, IntradayMomentumGao, NoiseAreaMomentum]


BUILTIN += _paper_strategies()


def load_user_strategies():
    """Import every strategies_user/*.py (files starting with '_' are skipped) and collect Strategy subclasses."""
    found, errors = [], {}
    if not USER_DIR.exists():
        return found, errors
    for f in sorted(USER_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"user_strategy_{f.stem}", f)
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            for obj in vars(mod).values():
                if isinstance(obj, type) and issubclass(obj, Strategy) and obj is not Strategy and obj not in BUILTIN:
                    found.append(obj)
        except Exception as e:                       # show the error in the app instead of crashing it
            errors[f.name] = repr(e)
    return found, errors


def registry():
    user, errors = load_user_strategies()
    return {cls.name: cls for cls in BUILTIN + user}, errors

import numpy as np
import pandas as pd
import pytest

from qpl.backtesting import accounting as A
from qpl.instruments import get
from qpl.prop_simulation import simulator as S
from qpl.statistics import metrics as M


def run(r, pnl, worst=None, ntr=None):
    pnl = np.asarray(pnl, float)
    worst = np.minimum(pnl, 0) if worst is None else np.asarray(worst, float)
    ntr = np.ones(len(pnl), np.int64) if ntr is None else np.asarray(ntr, np.int64)
    return S.run_eval(pnl, worst, ntr, r.start, r.target, r.mll, r.mll_type, r.lock_at_start, r.dll, r.dll_fail,
                      r.consistency, r.min_days, r.max_days)


def test_topstep_pass_requires_target_and_consistency():
    r = S.topstep_50k()
    # one huge day: 3000 in day 1 -> best day 3000 > 55% of 3000 -> not passed yet
    o, d, td, fp = run(r, [3000, 100, 100])
    assert o == S.TIMEOUT
    # need total >= 3000/0.55 = 5454.5
    o, d, td, fp = run(r, [3000, 1500, 1000])
    assert o == S.PASS and d == 3


def test_topstep_eod_trailing_floor_and_lock():
    r = S.topstep_50k()
    # +1500 EOD -> floor 49500; then a -1500 day touches 50000-... balance 51500-1500=50000 > 49500 ok
    o, *_ = run(r, [1500, -1500, 0])
    assert o == S.TIMEOUT
    # intraday dip below trailing floor fails even if the day closes green
    o, *_ = run(r, [1500, 100], worst=[0, -2001])
    assert o == S.FAIL_MLL
    # floor locks at start balance: after +2500 EOD the floor is 50000, not 50500
    o, *_ = run(r, [2500, -2400], worst=[0, -2400])
    assert o == S.TIMEOUT
    o, *_ = run(r, [2500, -2500], worst=[0, -2500])
    assert o == S.FAIL_MLL


def test_static_drawdown_and_daily_fail():
    r = S.ftmo_2step_100k()
    o, *_ = run(r, [-4000, -4000, -1999])
    assert o == S.TIMEOUT
    o, *_ = run(r, [-4000, -4000, -2000])
    assert o == S.FAIL_MLL
    o, *_ = run(r, [100, -10], worst=[0, -5000])
    assert o == S.FAIL_DLL


def test_dll_pause_mode_caps_day_loss():
    r = S.topstep_50k(dll=True)
    o, d, td, fp = run(r, [-1500, -100], worst=[-1500, -100])
    assert o == S.TIMEOUT and fp == pytest.approx(-1100)


def test_min_days():
    r = S.ftmo_2step_100k()
    o, d, *_ = run(r, [6000, 6000, 10, 10, 10], worst=[0, 0, 0, 0, 0])
    assert o == S.PASS and d == 4


def test_mc_runs_and_probabilities_sum_to_one():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"pnl": rng.normal(50, 400, 1000), "ntrades": 1})
    df["worst"] = np.minimum(df["pnl"], 0) - 100
    res = S.monte_carlo(df, S.topstep_50k(), n_sims=500)
    assert res["p_pass"] + res["p_fail"] + res["p_timeout"] == pytest.approx(1.0)
    assert 0.4 < res["p_pass"] < 1.0


def test_sizing_and_costs():
    inst = get("MES")
    tr = pd.DataFrame({"risk_pts": [10.0, 100.0, np.nan], "pnl_pts": [5.0, -10.0, 1.0], "mae_pts": [-2.0, -10.0, 0],
                       "reason": [2, 1, 4], "exit_i": [1, 2, 3], "entry_i": [0, 1, 2]})
    q = A.size_trades(tr, inst, risk_usd=200.0)
    # per contract risk = 10*5 + 0.74 + 2*1*1.25 = 53.24 -> 3 ; 100pt -> 0 (skipped) ; nan -> 0
    assert list(q) == [3, 0, 0]
    out = A.to_usd(tr, inst, q)
    assert len(out) == 1
    assert out.pnl_usd.iloc[0] == pytest.approx(3 * (5 * 5 - 0.74))
    out2 = A.to_usd(tr, inst, q, cost_mult=2, slip_mult=3)
    # target exit -> one slipped side; extra slip = 2 ticks * 0.25 = 0.5pt
    assert out2.pnl_usd.iloc[0] == pytest.approx(3 * ((5 - 0.5) * 5 - 1.48))


def test_daily_pnl_worst_includes_mae():
    trades = pd.DataFrame({"day": pd.to_datetime(["2024-01-02", "2024-01-02"]), "pnl_usd": [300.0, -200.0],
                           "mae_usd": [-50.0, -400.0]})
    days = pd.DatetimeIndex(pd.to_datetime(["2024-01-02", "2024-01-03"]))
    d = A.daily_pnl(trades, days)
    assert d.loc["2024-01-02", "pnl"] == 100 and d.loc["2024-01-02", "worst"] == -100
    assert d.loc["2024-01-03", "pnl"] == 0


def test_drawdown_and_streaks():
    eq = np.array([0, 10, 5, 12, 2, 20])
    assert M.drawdown(eq).min() == -10
    assert M.streaks(np.array([1, -1, -1, -1, 2, 2])) == (2, 3)

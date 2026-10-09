import numpy as np
from qpl.prop_simulation import ftmo_daily as FD


def test_pass_both_phases_and_payout():
    r = np.full(2000, 0.01)
    o = FD.simulate_start(r, 0)
    assert o["p1"] == FD.PASS and o["d1"] == 10 and o["p2"] == FD.PASS and o["d2"] == 5
    assert o["funded_status"] == "survived" and o["payout_frac"] > 0


def test_min_days_and_static_max_loss():
    r = np.zeros(100); r[0] = 0.2
    assert FD.simulate_start(r, 0)["d1"] == 4                       # target hit day 1, but needs 4 trading days
    r = np.full(100, -0.011)
    o = FD.simulate_start(r, 0, k=1.0, mode="optimistic")
    assert o["p1"] == FD.FAIL_MAX


def test_daily_loss_proxy_and_conservative_balance():
    r = np.zeros(50); r[3] = -0.04                                   # 4% close loss * 1.5 = 6% intraday > 5%
    assert FD.simulate_start(r, 0, mode="optimistic")["p1"] == FD.FAIL_DAILY
    r = np.zeros(50); r[1:4] = -0.02                                 # three -2% days: optimistic survives, conservative fails
    assert FD.simulate_start(r, 0, k=1.0, mode="optimistic")["p1"] != FD.FAIL_DAILY
    assert FD.simulate_start(r, 0, k=1.0, mode="conservative")["p1"] == FD.FAIL_DAILY

import numpy as np
from qpl.prop_simulation import cft_daily as C


def test_two_phase_pass_and_days():
    r = np.full(400, 0.01)
    o = C.simulate_start(r, 0, "2PHASE", mode="optimistic")
    assert o["result"] == C.PASS and o["p1"] == C.PASS and o["p2"] == C.PASS and o["days"] == 8 + 5


def test_one_phase_trailing_locks_at_initial():
    r = np.zeros(200); r[:5] = 0.02; r[5:15] = -0.007          # +10.4% then drawdown: floor = min(peak-6%, 1.0) = 1.0
    o = C.simulate_start(r, 0, "1PHASE", k=1.0, mode="optimistic")
    assert o["result"] == C.PASS                                 # target reached on day 5 before the drawdown
    r = np.zeros(200); r[:3] = 0.03; r[3:12] = -0.012           # peak ~1.093 -> floor 1.0 (locked): fails when equity < 1.0
    o = C.simulate_start(r, 0, "1PHASE", k=1.0, mode="optimistic")
    assert o["result"] == C.FAIL_MAX


def test_daily_loss_conservative_vs_optimistic():
    r = np.zeros(100); r[1:4] = -0.02
    assert C.simulate_start(r, 0, "1PHASE", k=1.0, mode="optimistic")["result"] != C.FAIL_DAILY
    assert C.simulate_start(r, 0, "1PHASE", k=1.0, mode="conservative")["result"] == C.FAIL_DAILY


def test_real_intraday_low_triggers_daily_breach():
    import numpy as np
    from qpl.prop_simulation import cft_daily as CFT
    r = np.array([0.01, 0.0, 0.01]); lo = np.array([0.0, -0.06, 0.0]); hi = np.zeros(3)
    out = CFT.simulate_start(r, 0, "2PHASE", mode="optimistic", lo=lo, hi=hi)
    assert out["result"] == CFT.FAIL_DAILY and out["days"] == 2
    # same closes without the wick: no breach
    out2 = CFT.simulate_start(r, 0, "2PHASE", mode="optimistic", lo=np.zeros(3), hi=hi, max_days=3)
    assert out2["result"] == CFT.OPEN


def test_pipeline_rebuys_after_fail_and_pays():
    import numpy as np
    from qpl.prop_simulation import cft_daily as CFT
    n = 400
    r = np.full(n, 0.004); lo = np.zeros(n); hi = np.zeros(n)
    lo[5] = -0.06                                     # first attempt breaches the daily loss on day 6
    out = CFT.pipeline(r, lo, hi, r, np.zeros(n), hi, 0, "2PHASE", fee=0.01, horizon=n)
    assert out["attempts"] == 2 and out["first_funded_days"] is not None and out["paid"] > 0
    assert abs(out["net"] - (out["paid"] - 0.02)) < 1e-12

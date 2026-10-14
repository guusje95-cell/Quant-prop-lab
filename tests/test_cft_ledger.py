import numpy as np

from qpl.prop_simulation.cft_ledger import run_ledger


def test_budget_and_cash_accounting():
    n = 300
    bad = np.full(n, -0.03)                                   # every challenge fails on the max-loss rule
    z = np.zeros(n)
    r = run_ledger(bad, bad, z, z, z, z, 0, "1PHASE", 100_000, 800, budget=3, horizon=n)
    assert r["bought"] == 3 and r["passed"] == 0 and abs(r["net"] + 2400) < 1e-6


def test_pass_then_payouts():
    n = 200
    up = np.full(n, 0.01); z = np.zeros(n)
    r = run_ledger(up, z, z, up, z, z, 0, "1PHASE", 100_000, 800, budget=1, horizon=n)
    assert r["passed"] == 1 and r["payouts"] >= 3 and r["net"] > 0
    assert abs(r["net"] - (r["paid"] - 800)) < 1e-6

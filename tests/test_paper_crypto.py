import math

import numpy as np
import pandas as pd
import pytest

from qpl.execution import paper_crypto as P


def synth(n=400, seed=1):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.02, n))
    l = np.minimum(o, c) * (1 - rng.uniform(0, 0.02, n))
    idx = pd.date_range("2020-01-01", periods=n, freq="1D", tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=idx)


def test_clean_room_signal_matches_research_implementation():
    # non-circular parity: paper_crypto does not import qpl.strategies; compare outputs on the same bars
    from qpl.strategies.crypto import trend_ensemble
    b = synth(600)
    ref = trend_ensemble(b, {}).to_numpy()
    s = P.CT1Signal()
    got = np.array([s.update(r.high, r.low, r.close) for r in b.itertuples()])
    assert np.allclose(got, ref, atol=1e-10)


def test_signal_parity_on_bitstamp_history():
    from qpl.data import crypto as CD
    from qpl.strategies.crypto import trend_ensemble
    try:
        b = CD.btc_bars("1D").loc["2016-01-01":]
    except Exception:
        pytest.skip("bitstamp data not available")
    ref = trend_ensemble(b, {}).to_numpy()
    s = P.CT1Signal()
    got = np.array([s.update(r.high, r.low, r.close) for r in b.itertuples()])
    assert np.max(np.abs(got - ref)) < 1e-9


def test_guard_rejects_duplicates_and_malformed():
    g = P.DataGuard()
    t = pd.Timestamp("2024-01-01", tz="UTC")
    assert g.check(t, 1, 2, 0.5, 1.5)
    assert not g.check(t, 1, 2, 0.5, 1.5)                                   # duplicate
    assert not g.check(t + pd.Timedelta(days=1), 1, 0.9, 0.5, 1.5)         # high < close
    assert g.check(t + pd.Timedelta(days=3), 1, 2, 0.5, 1.5)
    assert any(e["kind"] == "gap" for e in g.events)


def test_spot_account_never_shorts_and_perp_pays_funding():
    s = P.SpotAccount()
    s.rebalance("t", -0.5, 100.0)
    assert s.qty == 0
    p = P.PerpAccount(fee_bps=0, slip_bps=0)
    p.rebalance("t", 1.0, 100.0)
    eq0 = p.equity(100.0)
    p.settle_funding("t", 0.001, 100.0)                                     # long pays positive funding
    assert p.equity(100.0) == pytest.approx(eq0 - 0.001 * eq0)
    p.rebalance("t", -1.0, 100.0)
    eq1 = p.equity(100.0)
    p.settle_funding("t", 0.001, 100.0)                                     # short receives
    assert p.equity(100.0) > eq1


def test_perp_round_trip_pnl_and_fees():
    p = P.PerpAccount(cash=1000, fee_bps=10, slip_bps=0)
    p.rebalance("a", 1.0, 100.0)                                            # buy 10
    p.rebalance("b", 0.0, 110.0)                                            # sell 10 -> +100
    assert p.qty == pytest.approx(0, abs=1e-9)
    assert p.cash == pytest.approx(1000 + 100 - 10 * 100 * 1e-3 - 10 * 110 * 1e-3, rel=1e-6)


def test_liquidation_only_with_leverage():
    p = P.PerpAccount(cash=1000, max_leverage=1.0, fee_bps=0, slip_bps=0)
    p.rebalance("a", 1.0, 100.0)
    assert not p.liquidation_check("b", 51.0, 100.0)                       # -49% move at 1x: no liquidation
    q = P.PerpAccount(cash=1000, max_leverage=3.0, fee_bps=0, slip_bps=0)
    q.rebalance("a", 3.0, 100.0)
    assert q.liquidation_check("b", 66.0, 100.0) and q.liquidated


def test_checkpoint_restore_equals_continuous_run():
    b = synth(300, seed=4)
    fund = pd.Series(0.0001, index=pd.date_range("2020-01-01 08:00", periods=900, freq="8h", tz="UTC"))
    def run(split=None):
        r = P.CryptoPaperRunner(P.PerpAccount())
        for ts, rate in fund.items():
            r.add_funding(ts, rate)
        for i, row in enumerate(b.itertuples()):
            if split is not None and i == split:
                r = P.CryptoPaperRunner.restore(r.checkpoint())
            r.on_bar(row.Index, row.open, row.high, row.low, row.close)
        return r.acct.equity(b.close.iloc[-1])
    assert run() == pytest.approx(run(split=150), rel=1e-12)


def test_runner_has_no_lookahead():
    # changing a future bar must not change any earlier target
    b = synth(250, seed=7)
    def targets(df):
        r = P.CryptoPaperRunner(P.SpotAccount())
        for row in df.itertuples():
            r.on_bar(row.Index, row.open, row.high, row.low, row.close)
        return [h["w_target"] for h in r.history]
    a = targets(b)
    b2 = b.copy(); b2.iloc[200:, :] *= 1.5
    c = targets(b2)
    assert a[:200] == c[:200]


def test_warmup_places_no_orders():
    b = synth(200, seed=3)
    r = P.CryptoPaperRunner(P.PerpAccount())
    for row in b.iloc[:150].itertuples():
        r.warmup(row.Index, row.open, row.high, row.low, row.close)
    assert r.acct.fills == [] and r.acct.qty == 0 and r.acct.cash == 10_000.0
    row = b.iloc[150]
    r.on_bar(b.index[150], row.open, row.high, row.low, row.close)
    assert len(r.acct.fills) <= 1

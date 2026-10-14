import numpy as np
import pandas as pd
import pytest

from qpl.lab import data as D, engine as EN, strategies as S


def _bars(n=400, k=3, seed=0, freq="1d"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="D" if freq == "1d" else "h")
    c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, (n, k)), axis=0)), index=idx, columns=[f"A{i}" for i in range(k)])
    o = c.shift(1).fillna(c.iloc[0]); h = np.maximum(o, c) * 1.01; lo = np.minimum(o, c) * 0.99
    return D.Bars("synthetic", freq, o, h, lo, c, c * 0 + 1, D.PPY[freq])


@pytest.mark.parametrize("cls", [c for c in S.BUILTIN if c is not S.CStarTrend])
def test_builtin_strategies_have_no_lookahead(cls):
    b = _bars(); st = cls(); p = st.defaults()
    full = st.signal(b, p)
    cut = st.signal(b.select(end=b.close.index[299]), p)
    pd.testing.assert_frame_equal(full.iloc[:300], cut, check_freq=False)


def test_cstar_no_lookahead_without_filter():
    b = _bars(); st = S.CStarTrend(); p = {"stablecoin_filter": False, "long_only": True}
    pd.testing.assert_frame_equal(st.signal(b, p).iloc[:300], st.signal(b.select(end=b.close.index[299]), p), check_freq=False)


def test_engine_trades_next_bar_and_charges_costs():
    b = _bars(10, 1)
    w = pd.DataFrame(0.0, index=b.close.index, columns=b.symbols); w.iloc[3:, 0] = 1.0       # decided at close of bar 3
    r = EN.run(b, w, EN.Config(cost_bps=10))["bars"]
    ret = b.close["A0"].pct_change()
    assert r["gross"].iloc[3] == 0 and np.isclose(r["gross"].iloc[4], ret.iloc[4])
    assert np.isclose(r["cost"].iloc[4], 10 / 1e4) and r["cost"].iloc[5:].sum() == 0


def test_daily_aggregation_of_hourly_bars():
    b = _bars(48, 1, freq="1h")
    w = pd.DataFrame(1.0, index=b.close.index, columns=b.symbols)
    res = EN.run(b, w, EN.Config(cost_bps=0))["bars"]
    d = EN.to_daily(res, "1h")
    assert len(d) == 2 and np.isclose((1 + d["net"]).prod(), (1 + res["net"]).prod())
    assert (d["worst"] <= d["net"] + 1e-12).all()


def test_csv_import_long_and_single_asset():
    csv = "time,symbol,open,high,low,close\n2024-01-01,X,1,2,0.5,1.5\n2024-01-02,X,1.5,2,1,1.8\n2024-01-01,Y,10,11,9,10\n2024-01-02,Y,10,12,9,11\n"
    b = D.read_csv(csv.encode())
    assert b.symbols == ["X", "Y"] and b.freq == "1d" and b.close.loc["2024-01-02", "Y"] == 11
    b2 = D.read_csv(b"Date,Open,High,Low,Close\n2024-01-01,1,2,0.5,1.5\n2024-01-02,1.5,2,1,1.8\n")
    assert b2.symbols == ["ASSET"]


def test_user_strategy_template_loads(tmp_path, monkeypatch):
    src = (S.ROOT / "strategies_user/_template.py").read_text()
    (tmp_path / "mine.py").write_text(src)
    monkeypatch.setattr(S, "USER_DIR", tmp_path)
    reg, errs = S.registry()
    assert not errs and "My example: N-day high breakout" in reg
    b = _bars(); st = reg["My example: N-day high breakout"]()
    sig = st.signal(b, st.defaults())
    assert sig.shape == b.close.shape and set(np.unique(sig.values)) <= {0.0, 1.0}


# ------------------------------------------------------------------ paper strategies
from qpl.lab import strategies_papers as SP  # noqa: E402


def _pairs_bars(n=900, seed=3):
    """Two cointegrated assets (y = 1.5 x + mean-reverting noise) and one unrelated random walk."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="D")
    x = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    u = np.zeros(n)
    for t in range(1, n):
        u[t] = 0.8 * u[t - 1] + rng.normal(0, 1.0)
    y = 1.5 * x + u
    z = 50 * np.exp(np.cumsum(rng.normal(0, 0.015, n)))
    c = pd.DataFrame({"X": x, "Y": y, "Z": z}, index=idx)
    return D.Bars("pairs", "1d", c, c, c, c, c * np.nan, 252)


def test_engle_granger_matches_statsmodels():
    from statsmodels.tsa.stattools import coint
    b = _pairs_bars()
    for a, c in (("Y", "X"), ("Z", "X")):
        assert np.isclose(SP.engle_granger(b.close[a].to_numpy(), b.close[c].to_numpy()), coint(b.close[a], b.close[c])[1], atol=1e-8)


def test_kalman_pairs_finds_the_cointegrated_pair_and_has_no_lookahead():
    b = _pairs_bars(); st = SP.KalmanPairs(); p = dict(st.defaults(), formation_days=365, reselect_days=0)
    full = st.signal(b, p)
    assert set(st.info["pair"]) == {"Y / X"} and (full["Z"] == 0).all() and (full != 0).any().any()
    assert np.allclose(full["Y"] * full["X"], -abs(full["Y"] * full["X"]))          # always opposite sides
    cut = st.signal(b.select(end=b.close.index[699]), p)
    pd.testing.assert_frame_equal(full.iloc[:700], cut, check_freq=False)


def test_pair_position_rules():
    z = np.array([0, -1.0, -1.5, -1.3, -1.2, -0.5, 0.0, 0.1, 0.5, 1.5, 1.2, 0.0, -0.1])
    d = SP.pair_positions(z, 1.25, 0.08, True, 0.0)
    assert list(d) == [0, 0, 0, 0, 1, 1, 1, 0, 0, 0, -1, -1, 0]       # delayed entry: re-cross of -1.25 / +1.25
    i = SP.pair_positions(z, 1.25, 0.08, False, 0.0)
    assert i[2] == 1 and i[7] == 0 and i[9] == -1 and i[12] == 0


def _intraday_bars(days=500, seed=5):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2021-01-04 13:00", periods=days * 96, freq="15min")
    idx = idx[idx.dayofweek < 5]
    c = pd.Series(15000 * np.exp(np.cumsum(rng.normal(0, 0.001, len(idx)))), index=idx)
    o = c.shift(1).fillna(c.iloc[0]); h = np.maximum(o, c) * (1 + rng.uniform(0, 0.001, len(c))); lo = np.minimum(o, c) * (1 - rng.uniform(0, 0.001, len(c)))
    f = lambda s: s.to_frame("NQ")
    return D.Bars("nq", "15m", f(o), f(h), f(lo), f(c), f(c * 0 + 100), D.periods_per_year(idx, "15m"))


def test_maxai_no_lookahead_session_only_and_trains_before_trading():
    b = _intraday_bars(); st = SP.MaxAIQLearning(); p = dict(st.defaults(), train_days=120, retrain_days=60, min_visits=5)
    full = st.signal(b, p)
    assert (full.loc[: b.close.index[0] + pd.Timedelta(days=120)] == 0).all().all()
    ny = full.index.tz_localize("UTC").tz_convert("America/New_York")
    mins = ny.hour * 60 + ny.minute
    assert (full["NQ"][(mins < 570) | (mins + 15 > 960)] == 0).all()                  # flat outside 9:30-16:00 ET
    assert (full["NQ"] != 0).any()
    n = len(b.close) * 2 // 3
    cut = st.signal(b.select(end=b.close.index[n - 1]), p)
    pd.testing.assert_frame_equal(full.iloc[:n], cut, check_freq=False)


def test_stop_loss_and_target_exits():
    a = np.ones(8); c = np.array([100, 100, 99.6, 99.6, 99.6, 100, 100, 100.0]); tr = np.ones(8, bool)
    pos = SP._with_exits(a, c, tr, 0.003, 0.005, True)
    assert list(pos) == [1, 1, 0, 0, 0, 0, 0, 0]                         # stopped out, waits for the policy to change
    a2 = np.array([1, 1, 0, 1, 1, 1, -1, -1.0]); c2 = np.array([100, 100.6, 100.6, 100, 100.2, 100.6, 100, 100.0])
    pos2 = SP._with_exits(a2, c2, tr, 0.003, 0.005, True)
    assert list(pos2) == [1, 0, 0, 1, 1, 0, -1, -1]                        # target, re-entry after neutral, target, short


@pytest.mark.parametrize("cls", [SP.IntradayMomentumGao, SP.NoiseAreaMomentum])
def test_intraday_momentum_no_lookahead_and_flat_overnight(cls):
    rng = np.random.default_rng(11)
    idx = pd.date_range("2022-01-03", periods=120 * 288, freq="5min")
    c = pd.Series(4000 * np.exp(np.cumsum(rng.normal(0, 0.0008, len(idx)))), index=idx)
    o = c.shift(1).fillna(c.iloc[0]); f = lambda s: s.to_frame("ES")
    b = D.Bars("es", "5m", f(o), f(np.maximum(o, c) * 1.0003), f(np.minimum(o, c) * 0.9997), f(c), f(c * 0 + 10), D.periods_per_year(idx, "5m"))
    st = cls(); full = st.signal(b, st.defaults())
    assert (full["ES"] != 0).any()
    ses = SP.ny_session(idx, "5m")
    assert (full["ES"][~ses.insess | ses["last"]] == 0).all()                     # never held over 16:00 or outside the session
    n = len(idx) * 3 // 4
    pd.testing.assert_frame_equal(full.iloc[:n], st.signal(b.select(end=idx[n - 1]), st.defaults()), check_freq=False)


def test_dukascopy_minute_decoder_and_price_scale(tmp_path, monkeypatch):
    """Dukascopy minute files: LZMA, 24-byte big-endian records; the price scale must be inferred and range-checked."""
    import lzma
    from qpl.lab import download as DL
    rec = np.zeros(3, dtype=[("t", ">u4"), ("o", ">i4"), ("c", ">i4"), ("l", ">i4"), ("h", ">i4"), ("v", ">f4")])
    rec["t"] = [0, 60, 120]; rec["o"] = [15000_000, 15001_000, 15002_000]; rec["c"] = [15001_000, 15002_000, 15003_500]
    rec["l"] = rec["o"] - 500; rec["h"] = rec["c"] + 500; rec["v"] = [1.5, 2.0, 0.0]
    blob = lzma.compress(rec.tobytes(), format=lzma.FORMAT_ALONE)

    class R:
        status_code, content = 200, blob
        def raise_for_status(self): pass
    monkeypatch.setattr(DL.requests, "get", lambda *a, **k: R())
    monkeypatch.setattr(DL, "LAB", tmp_path)
    df = DL.dukascopy("US100", start="2024-01-02", end="2024-01-02", pause=0)
    assert list(df["close"]) == [15001.0, 15002.0]                    # zero-volume minute dropped, scale 10^3 found
    assert df["time"].iloc[1] == pd.Timestamp("2024-01-02 00:01") and (df["high"] >= df["close"]).all()


# ------------------------------------------------------------------ prop-firm engine
from qpl.lab import propfirms as PF  # noqa: E402


def _daily(net, worst=None, best=None, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(net), freq="D")
    net = np.asarray(net, float)
    return pd.DataFrame({"net": net, "worst": np.minimum(net, 0) if worst is None else worst,
                         "best": np.maximum(net, 0) if best is None else best}, index=idx)


def test_prop_pass_daily_loss_and_trailing_lock():
    f = PF.Firm(targets=(0.10,), daily_loss=0.04, daily_basis="initial", max_loss=0.06, max_type="trailing_lock")
    r, lo, hi = PF._arrays(_daily([0.01] * 30), 1.0)
    cal = np.arange(30)
    assert PF._phase(r, lo, hi, cal, 0, 30, 0.10, f) == (PF.PASS, 10)                  # 1.01^10 >= 1.10 on day 10
    d = _daily([0.0, -0.01], worst=[0.0, -0.045]); r, lo, hi = PF._arrays(d, 1.0)
    assert PF._phase(r, lo, hi, np.arange(2), 0, 2, 0.10, f)[0] == PF.FAIL_DAILY          # intraday -4.5% breaks the 4% limit
    # up 8% (trailing floor 1.02 -> locked at 1.00), then two -3% days: the 2nd ends at ~1.016 * ... below the floor
    d = _daily([0.04, 0.0385, -0.03, -0.035, -0.035]); r, lo, hi = PF._arrays(d, 1.0)
    res, day = PF._phase(r, lo, hi, np.arange(5), 0, 5, 0.20, f)
    assert res == PF.FAIL_MAX and day == 5
    f2 = PF.replace(f, max_type="static")
    assert PF._phase(r, lo, hi, np.arange(5), 0, 5, 0.20, f2)[0] == PF.OPEN             # static 6% floor (0.94) never hit


def test_prop_min_days_and_two_phases():
    f = PF.Firm(targets=(0.08, 0.05), daily_loss=0.05, max_loss=0.10, min_days=4)
    d = _daily([0.10] + [0.0] * 3 + [0.001] * 3 + [0.06] + [0.001] * 3 + [0.0] * 3)
    r, lo, hi = PF._arrays(d, 1.0)
    res, t = PF._challenge(r, lo, hi, np.arange(len(d)), 0, len(d), f)
    assert res == PF.PASS and t == 11        # each phase needs 4 TRADING days (flat days do not count): rows 0,4,5,6 then 7..10


def test_prop_pipeline_fees_payouts_and_parallel_accounts():
    f = PF.Firm(account=100_000, fee=500, targets=(0.05,), daily_loss=0.05, max_loss=0.10, split=0.8, payout_every=30, refund_fee=True)
    d = _daily([0.001] * 900)
    one = PF.pipeline(d, f, budget=3, accounts=1, scale_c=1.0, scale_f=1.0, horizon_days=730, step=30)
    two = PF.pipeline(d, f, budget=3, accounts=2, scale_c=1.0, scale_f=1.0, horizon_days=730, step=30)
    assert one["P_funded"] == 1.0 and one["bought"] == 1 and one["fees"] == 500
    assert np.isclose(two["net_mean"], 2 * one["net_mean"]) and one["net_mean"] > 0
    # funded income ~ 0.8 * (1.001^30 - 1) * 100k per 30 days, plus the refunded fee once
    assert 0.8 * 0.0304 * 100_000 * 18 < one["paid"] < 0.8 * 0.0304 * 100_000 * 24 + 500
    fm = PF.replace(f, fee_monthly=True, refund_fee=False)
    slow = PF.pipeline(_daily([0.0005] * 900), fm, budget=1, accounts=1, horizon_days=730, step=30)
    assert slow["fees"] > 500                                                   # subscription renewed while the target takes ~100 days


def test_prop_presets_run_on_any_daily_series():
    d = _daily(np.random.default_rng(0).normal(0.001, 0.01, 800))
    for f in PF.PRESETS.values():
        a = PF.attempts(d, f); p = PF.pipeline(d, f, budget=3, horizon_days=365)
        assert abs(a["P_pass"] + a["P_fail_daily"] + a["P_fail_max"] + a["P_fail_time"] + a["P_open"] - 1) < 1e-9
        assert 0 <= p["P_funded"] <= 1

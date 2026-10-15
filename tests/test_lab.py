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
    monkeypatch.setattr(DL, "_duka_get", lambda url: R())
    monkeypatch.setattr(DL, "_pace", lambda ok: None)
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


# ------------------------------------------------------------------ gen48 paper strategies
def _hourly_panel(days=420, k=3, seed=21):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2021-01-04", periods=days * 24, freq="h")
    c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.00002, 0.003, (len(idx), k)), axis=0)), index=idx, columns=[f"X{i}" for i in range(k)])
    o = c.shift(1).fillna(c.iloc[0])
    return D.Bars("h", "1h", o, np.maximum(o, c), np.minimum(o, c), c, c * 0 + 1, D.periods_per_year(idx, "1h"))


@pytest.mark.parametrize("mode", ["TTSM-S2 (paper best)", "TTSM-S1", "TSM (no semivariance filter)"])
def test_semivariance_tsmom_no_lookahead_and_daily_constant(mode):
    b = _hourly_panel(); st = SP.SemivarianceTSMOM(); p = dict(st.defaults(), mode=mode, ref_window=120)
    full = st.signal(b, p)
    assert (full != 0).any().any()
    day = full.index.floor("D")
    assert (full.groupby(day).nunique() <= 1).all().all()                            # one position per asset per day
    n = len(b.close) * 3 // 4 + 7                                                     # cut in the middle of a day
    pd.testing.assert_frame_equal(full.iloc[:n], st.signal(b.select(end=b.close.index[n - 1]), p), check_freq=False)


def test_semivariance_regions_s1_s2():
    # RS- high only (region 2): S1 -> short regardless of momentum; S2 -> longs short, shorts flat
    tsm = pd.Series([1.0, -1.0]); r2 = pd.Series([True, True])
    s1 = tsm.copy(); s1[r2] = -1.0
    s2 = tsm.copy(); s2[r2] = np.where(tsm[r2] > 0, -1.0, 0.0)
    assert list(s1) == [-1, -1] and list(s2) == [-1, 0]


def test_vol_managed_monthly_weights_known_in_advance():
    b = _bars(900, 1); st = SP.VolatilityManaged(); p = st.defaults()
    full = st.signal(b, p)
    m = full.index.to_period("M")
    inside = full["A0"].groupby(m).nunique()
    assert (inside[inside.index > inside.index[13]] <= 2).all()                      # constant within a month (+1-day switch lag)
    pd.testing.assert_frame_equal(full.iloc[:600], st.signal(b.select(end=b.close.index[599]), p), check_freq=False)
    capped = st.signal(b, dict(p, max_leverage=1.5))
    assert capped["A0"].max() <= 1.5 + 1e-12


def test_european_open_window():
    idx = pd.date_range("2024-01-08 00:00", periods=4 * 24 * 3, freq="15min")       # UTC, winter: NY = UTC-5
    c = pd.DataFrame({"US500": np.linspace(100, 101, len(idx))}, index=idx)
    b = D.Bars("x", "15m", c, c, c, c, c * 0 + 1, 252 * 96)
    w = SP.EuropeanOpen().signal(b, SP.EuropeanOpen().defaults())["US500"]
    # a weight set at the close of the 04:15-04:30 UTC bar (= 23:30 NY) is held 23:30-23:45 NY; the last held bar ends 03:30 NY
    assert w.loc["2024-01-08 04:15"] == 1 and w.loc["2024-01-08 04:00"] == 0
    assert w.loc["2024-01-08 08:00"] == 1 and w.loc["2024-01-08 08:15"] == 0           # bar ending 08:30 UTC = 03:30 NY -> flat
    assert abs(w.mean() - 16 / 96) < 0.02                                              # 4 hours of 24


def test_curve_momentum_picks_backwardated_contract_and_no_lookahead():
    rng = np.random.default_rng(4)
    idx = pd.bdate_range("2010-01-01", periods=900)
    cols, slope = {}, {}
    for i in range(6):
        for k in range(2):
            cols[f"C{i}#{k}"] = 100 * np.exp(np.cumsum(rng.normal(0.0003 * (i - 2.5), 0.01, len(idx))))
            slope[f"C{i}#{k}"] = np.full(len(idx), 0.05 if k == 1 else -0.05)          # slot 1 always more backwardated
    c = pd.DataFrame(cols, index=idx)
    b = D.Bars("curve", "1d", c, c, c, c, c * np.nan, 252, {"slope": pd.DataFrame(slope, index=idx)})
    st = SP.CurveMomentum(); p = st.defaults()
    w = st.signal(b, p)
    last = w.iloc[-1]
    assert (last[[f"C{i}#1" for i in range(6)]] > 0).sum() == 3 and (last[[f"C{i}#0" for i in range(6)]] < 0).sum() == 3
    assert np.isclose(last[last > 0].sum(), 1) and np.isclose(last[last < 0].sum(), -1)
    pd.testing.assert_frame_equal(w.iloc[:700], st.signal(b.select(end=idx[699]), p), check_freq=False)


def test_daily_equity_stop_caps_the_day_and_avoids_daily_breach():
    f = PF.Firm(targets=(0.5,), daily_loss=0.04, daily_basis="initial", max_loss=0.10, stop_frac=0.75, stop_slip=0.003)
    d = _daily([0.0, -0.02], worst=[0.0, -0.06])                     # -6% intraday low, closes -2%
    r, lo, hi = PF._arrays(d, 1.0)
    res, _ = PF._phase(r, lo, hi, np.arange(2), 0, 2, 0.5, f)
    assert res == PF.OPEN                                              # without the stop this day breaks the 4% limit
    assert PF._phase(r, lo, hi, np.arange(2), 0, 2, 0.5, PF.replace(f, stop_frac=0.0))[0] == PF.FAIL_DAILY
    low, close, high = PF._day(f, 1.0, 1.0, -0.02, -0.06, 0.0)
    assert np.isclose(close, 1 - 0.033) and np.isclose(low, close)     # out at -3% minus 0.3% slippage


def test_catching_crypto_trends_ensemble_no_lookahead():
    b = _bars(500, 2); st = S.CryptoTrendEnsemble(); p = dict(st.defaults(), lookbacks="5,10,20,30")
    full = st.signal(b, p)
    assert full.max().max() <= 1 and full.min().min() >= 0 and (full > 0).any().any()
    pd.testing.assert_frame_equal(full.iloc[:300], st.signal(b.select(end=b.close.index[299]), p), check_freq=False)


def test_no_trade_band_keeps_small_changes():
    w = pd.DataFrame({"A": [0.0, 1.0, 1.1, 1.3, -0.5, -0.55]})
    out = EN.apply_band(w, 0.2)["A"].tolist()
    assert out == [0.0, 1.0, 1.0, 1.3, -0.5, -0.5]


def test_cstar_btc_leads_zeroes_alts_when_btc_is_flat():
    b = _bars(400, 3); b.close.columns = ["BTC", "ETH", "SOL"]
    for k in ("open", "high", "low", "volume"):
        getattr(b, k).columns = ["BTC", "ETH", "SOL"]
    st = S.CStarTrend(); p = {"stablecoin_filter": False, "long_only": True, "btc_leads": True}
    s = st.signal(b, p); base = st.signal(b, dict(p, btc_leads=False))
    off = base["BTC"] <= 0
    assert (s.loc[off, ["ETH", "SOL"]] == 0).all().all() and s["BTC"].equals(base["BTC"])
    assert (s.loc[~off, ["ETH", "SOL"]] == base.loc[~off, ["ETH", "SOL"]]).all().all()


def test_binance_vision_zip_parser_handles_header_and_microseconds(monkeypatch):
    import io as _io, zipfile as _zf
    from qpl.lab import binance_vision as BV
    def mk(text):
        b = _io.BytesIO()
        with _zf.ZipFile(b, "w") as z:
            z.writestr("x.csv", text)
        return b.getvalue()
    class R:
        def __init__(self, c): self.status_code, self.content = 200, c
        def raise_for_status(self): pass
    hdr = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n"
    row_ms = "1704067200000,1,2,0.5,1.5,10,1704067259999,15,3,4,6,0\n"
    row_us = "1735689600000000,1,2,0.5,1.5,10,1735689659999999,15,3,4,6,0\n"
    monkeypatch.setattr(BV.requests, "get", lambda *a, **k: R(mk(hdr + row_ms)))
    d1 = BV._zip_csv("u"); assert list(d1.columns)[:2] == ["open_time", "open"] and len(d1) == 1
    monkeypatch.setattr(BV.requests, "get", lambda *a, **k: R(mk(row_us)))
    d2 = BV._zip_csv("u"); assert len(d2) == 1 and d2.shape[1] == 12
    ts = pd.to_numeric(d2.iloc[:, 0]); assert pd.to_datetime(ts, unit="us" if ts.max() > 1e14 else "ms")[0] == pd.Timestamp("2025-01-01")


def test_payout_min_and_first_payout_delay():
    import numpy as np, pandas as pd
    from qpl.lab import propfirms as PF
    idx = pd.date_range("2024-01-01", periods=120, freq="D")
    d = pd.DataFrame({"net": 0.002, "worst": -0.001, "best": 0.003}, index=idx)
    base = PF.Firm("t", 100_000, 100, (0.01,), 0.05, "initial", True, 0.10, "static", True, 0, 0, 0.8, 7, 0.0, False, 0.0)
    rows = [d[c].to_numpy() for c in ("net", "worst", "best")]
    cal = np.arange(len(idx))
    a = PF._ledger(*rows, *rows, cal, 0, len(idx), base, 1)
    b = PF._ledger(*rows, *rows, cal, 0, len(idx), PF.replace(base, first_payout_days=21), 1)
    c = PF._ledger(*rows, *rows, cal, 0, len(idx), PF.replace(base, payout_min=50_000), 1)
    assert b["first_pay"] - a["first_pay"] == 14          # first payout 21 days after funding instead of 7
    assert c["payouts"] == 0 and a["payouts"] > 5         # profits accumulate but never reach a $50k payout in 120 days
    assert PF.PRESETS["SizeProp Degen $100k"].reset_hour_utc == 20 and PF.PRESETS["Breakout One-Step Classic $100k"].swap_bps_day == 3.3

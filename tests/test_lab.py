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

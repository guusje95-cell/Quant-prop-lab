"""Paper trader v2: NON-circular parity (clean-room signal vs backtester), restart/recovery,
data-quality guard and rule-breach edge cases."""
import math

import numpy as np
import pandas as pd
import pytest

from qpl.data import loaders
from qpl.execution import paper_v2 as PV
from qpl.instruments import get
from qpl.research import pipeline as P

FR = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)
CFG = dict(symbol="MNQ", tick=0.25, point_value=2.0, commission_rt=0.74, slip_ticks=1.0, account={"mll": 1e9, "target": 1e12},
           kill_z=-1e9)   # parity runs: rules and kill switch disabled so only signal/execution logic is compared


def _bt(df, inst):
    from qpl.strategies import index_intraday as SI
    from qpl.backtesting import engine as E
    from qpl.backtesting import accounting as A
    ctx = SI.build_context(df, 15)
    tr = E.run(ctx, SI.noise_area(ctx, FR), SI.rth_session(ctx), inst.tick_size, 0)
    return A.to_usd(tr, inst, np.ones(len(tr), np.int64))


@pytest.mark.parametrize("source,sym,a,b", [("dukascopy", "US100", "2016-01-01", "2016-12-31"),
                                            ("dukascopy", "US100", "2022-01-01", "2022-06-30"),
                                            ("topstepx", "MNQ", None, None)])
def test_clean_room_matches_backtester(tmp_path, source, sym, a, b):
    df = loaders.load(source, sym, "15min" if source == "topstepx" else "M15")
    if a:
        df = df.loc[a:b]
    inst = get("MNQ")
    r = PV.replay(df, PV.RunnerConfig(**CFG), tmp_path)
    paper = pd.DataFrame(r.trades)
    bt = _bt(df, inst)
    assert len(bt) > 10
    assert len(paper) == len(bt)
    assert (pd.DatetimeIndex(paper.entry_ts) == pd.DatetimeIndex(bt.entry_ts)).all()
    assert np.array_equal(paper.dir.to_numpy(), bt.dir.to_numpy())
    assert np.allclose(paper.pnl_usd.to_numpy(), bt.pnl_usd.to_numpy(), atol=1e-6)


def test_restart_recovery_gives_identical_results(tmp_path):
    df = loaders.load("dukascopy", "US100", "M15").loc["2017-01-01":"2017-06-30"]
    full = PV.replay(df, PV.RunnerConfig(**CFG), tmp_path / "a")
    cut = len(df) // 2
    r = PV.replay(df.iloc[:cut], PV.RunnerConfig(**CFG), tmp_path / "b")
    r.checkpoint(tmp_path / "ck.json")
    r2 = PV.PaperRunner.restore(tmp_path / "ck.json", PV.RunnerConfig(**CFG), tmp_path / "b")
    for ts, row in df.iloc[cut:].iterrows():
        r2.on_bar(ts, row.open, row.high, row.low, row.close)
    assert len(r2.trades) == len(full.trades)
    assert np.allclose([t["pnl_usd"] for t in r2.trades], [t["pnl_usd"] for t in full.trades])


def test_data_guard_rejects_bad_bars():
    g = PV.DataGuard(15)
    t0 = pd.Timestamp("2024-01-02 15:00", tz="UTC")
    assert g.check(t0, 10, 11, 9, 10)
    assert not g.check(t0, 10, 11, 9, 10)                         # duplicate
    assert not g.check(t0 + pd.Timedelta(minutes=15), 10, 9, 11, 10)  # high < low
    assert not g.check(t0 + pd.Timedelta(minutes=30), 10, 11, 9, float("nan"))


def test_mll_breach_liquidates_and_stops_trading(tmp_path):
    r = PV.PaperRunner(PV.RunnerConfig(**{**CFG, "account": {"mll": 50.0, "start": 50000.0, "floor": 49950.0}}), tmp_path)
    r.brk.pos, r.brk.qty, r.brk.entry_px, r.brk.entry_ts = 1, 1, 100.0, pd.Timestamp("2024-01-02 15:00", tz="UTC")
    r.on_bar(pd.Timestamp("2024-01-02 15:15", tz="UTC"), 100.0, 100.5, 60.0, 70.0)
    assert r.risk.a.status == "FAILED_MLL" and r.brk.pos == 0 and not r.risk.allow_entry()


def test_kill_switch_triggers_on_drift():
    rm = PV.RiskManager(PV.Account(), kill_min_trades=30)
    z = rm.monitor([-100.0] * 30)
    assert z < -2 and rm.kill and not rm.allow_entry()

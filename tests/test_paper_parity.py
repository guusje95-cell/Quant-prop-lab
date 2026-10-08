"""Parity: the independent event-driven paper trader must reproduce the backtester's trades
on real futures data (TopstepX MNQ 15-minute bars)."""
import numpy as np
import pandas as pd
import pytest

from qpl.data import loaders
from qpl.execution.paper import PaperConfig, replay
from qpl.instruments import get
from qpl.research import pipeline as P


def test_paper_matches_backtest(tmp_path):
    df = loaders.load("topstepx", "MNQ", "15min")
    cfg = PaperConfig(symbol="MNQ", risk_budget_per_sd=None, fixed_contracts=1, mll=1e9)
    pt = replay(df, cfg, tmp_path)
    paper = pd.DataFrame(pt.trades)
    ctx = P.context("topstepx", "MNQ", "15min")
    inst = get("MNQ")
    bt = P.usd(P.backtest("noise_area", ctx, cfg.params, inst), inst, contracts=1, norm=False)
    assert len(paper) == len(bt) and len(bt) > 10
    assert np.array_equal(paper.dir.to_numpy(), bt.dir.to_numpy())
    assert (pd.DatetimeIndex(paper.entry_ts) == pd.DatetimeIndex(bt.entry_ts)).all()
    assert np.allclose(paper.pnl_usd.to_numpy(), bt.pnl_usd.to_numpy(), atol=1e-6)

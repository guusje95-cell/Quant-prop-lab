import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from qpl.strategies import futures_factors as FF

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/raw/ext/pysystemtrade/data/futures"


def test_tsmom_matches_independent_loop():
    rng = np.random.default_rng(5)
    r = pd.DataFrame({"A": rng.normal(0.0003, 0.01, 800)}, index=pd.date_range("2001-01-01", periods=800, freq="B"))
    lib = FF.tsmom(r, (63, 126, 252))["A"].to_numpy()
    lp = np.cumsum(np.log1p(r["A"].to_numpy()))
    for t in range(300, 800, 37):
        exp = np.mean([np.sign(lp[t] - lp[t - L]) for L in (63, 126, 252)])
        assert lib[t] == pytest.approx(exp)


def test_ewmac_matches_independent_formula():
    rng = np.random.default_rng(6)
    r = pd.DataFrame({"A": rng.normal(0.0002, 0.01, 1500)}, index=pd.date_range("2001-01-01", periods=1500, freq="B"))
    lib = FF.ewmac(r, ((16, 64),))["A"].to_numpy()
    x = np.cumsum(np.log1p(r["A"].to_numpy()))
    def ema(v, span):
        a = 2 / (span + 1); out = np.empty_like(v); m = v[0]; num = 0; den = 0
        for i, vi in enumerate(v):                       # pandas adjust=True EMA
            num = vi + (1 - a) * num; den = 1 + (1 - a) * den; out[i] = num / den
        return out
    raw = (ema(x, 16) - ema(x, 64)) / pd.Series(r["A"]).ewm(span=35, min_periods=20).std().to_numpy()
    raw[:63] = np.nan                                   # slow EMA needs 64 observations (spec: min_periods = span)
    scale = pd.Series(np.abs(raw)).expanding(min_periods=256).mean().to_numpy()
    exp = np.clip(raw / scale, -2, 2) / 2
    ok = np.isfinite(exp) & (np.arange(len(exp)) >= 300)
    assert np.allclose(lib[ok], exp[ok], atol=1e-9)


@pytest.mark.skipif(not SRC.exists(), reason="pysystemtrade data not present")
def test_paper_book_two_day_replay(tmp_path):
    from qpl.data import futures_panel as FP
    from qpl.execution.paper_futures import FuturesPaperBook
    names = ["SP500", "US10", "GOLD", "CRUDE_W", "EUR", "CORN", "BUND", "JPY", "NASDAQ", "COPPER"]
    def make(cut):
        d = tmp_path / f"data_{cut}"
        for sub in ("adjusted_prices_csv", "multiple_prices_csv"):
            (d / sub).mkdir(parents=True)
            for n in names:
                df = pd.read_csv(SRC / sub / f"{n}.csv", parse_dates=["DATETIME"])
                df[df.DATETIME < cut].to_csv(d / sub / f"{n}.csv", index=False)
        shutil.copytree(SRC / "csvconfig", d / "csvconfig"); shutil.copytree(SRC / "fx_prices_csv", d / "fx_prices_csv")
        return d
    old_src, old_proc = FP.SRC, FP.PROC
    try:
        state = tmp_path / "f9.json"
        recs = []
        for cut in ("2023-06-01", "2023-06-02", "2023-06-02"):
            FP.set_source(make(cut) if not (tmp_path / f"data_{cut}").exists() else tmp_path / f"data_{cut}", tmp_path / f"proc_{cut}")
            P = FP.build(force=True); U, _ = FP.universe(P)
            recs.append(FuturesPaperBook(1e7, state).step(P, U, {k: k for k in U}))
        assert recs[0]["orders"] > 0
        assert recs[2] == {"status": "no new data", "last_date": recs[1]["date"]}     # idempotent re-run
        import json
        st = json.loads(state.read_text())
        assert any(v != 0 for v in st["held"].values())                                  # day-1 orders were filled on day 2
    finally:
        FP.SRC, FP.PROC = old_src, old_proc

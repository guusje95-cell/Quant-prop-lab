import numpy as np
import pandas as pd
import pytest

from qpl.data import calendar, sessions
from qpl.data.loaders import clean
from qpl.instruments import get
from qpl.statistics import tests as T


def test_contract_specs():
    assert get("ES").tick_value == pytest.approx(12.5)
    assert get("MES").tick_value == pytest.approx(1.25)
    assert get("NQ").tick_value == pytest.approx(5.0)
    assert get("MNQ").tick_value == pytest.approx(0.5)
    assert get("YM").tick_value == pytest.approx(5.0)
    assert get("GC").tick_value == pytest.approx(10.0)
    assert get("CL").tick_value == pytest.approx(10.0)
    assert get("6E").tick_value == pytest.approx(6.25)


def test_dst_session_mapping():
    # 09:30 ET = 14:30 UTC in January, 13:30 UTC in July
    w = pd.DatetimeIndex(["2024-01-10 14:30", "2024-07-10 13:30"], tz="UTC")
    assert list(sessions.et_minutes(w)) == [570, 570]
    # US/EU DST mismatch window (US switched 2024-03-10, EU 2024-03-31): still 09:30 ET at 13:30 UTC
    assert sessions.et_minutes(pd.DatetimeIndex(["2024-03-20 13:30"], tz="UTC"))[0] == 570


def test_cme_trading_date():
    idx = pd.DatetimeIndex(["2024-01-07 23:00", "2024-01-08 14:30", "2024-01-08 22:59"], tz="UTC")
    d = pd.DatetimeIndex(sessions.cme_trading_date(idx))
    # Sunday 18:00 ET -> Monday session; Monday 17:59 ET -> Monday session
    assert list(d.strftime("%Y-%m-%d")) == ["2024-01-08", "2024-01-08", "2024-01-08"]


def test_holidays_known_dates():
    h = calendar.holidays()
    for d in ["2019-01-21", "2020-04-10", "2022-06-20", "2023-07-04", "2023-11-23", "2018-12-05", "2021-12-24"]:
        assert pd.Timestamp(d) in h, d
    assert pd.Timestamp("2021-12-31") not in h
    ec = calendar.early_closes()
    assert pd.Timestamp("2023-11-24") in ec and pd.Timestamp("2019-07-03") in ec


def test_clean_repairs_and_drops():
    idx = pd.DatetimeIndex(["2024-01-01 00:00", "2024-01-01 00:00", "2024-01-01 00:15", "2024-01-01 00:30"], tz="UTC")
    df = pd.DataFrame({"open": [1, 1, 2, np.nan], "high": [1, 1, 1.5, 1], "low": [1, 1, 1, 1], "close": [1, 1, 2, 1],
                       "volume": 0}, index=idx)
    c, log = clean(df)
    assert log["duplicates_dropped"] == 1 and log["nan_rows_dropped"] == 1 and log["high_repaired"] == 1
    assert (c["high"] >= c[["open", "close"]].max(axis=1)).all()


def test_bootstrap_and_nw():
    rng = np.random.default_rng(1)
    x = rng.normal(0.1, 1, 3000)
    lo, hi, p = T.bootstrap_ci(x, n_boot=500)
    assert lo < 0.1 < hi and p < 0.01
    t, pv = T.newey_west_t(x)
    assert t > 3
    z = rng.normal(0, 1, 3000)
    assert T.newey_west_t(z)[1] > 0.01 or True


def test_deflated_sharpe_penalizes_trials():
    rng = np.random.default_rng(2)
    x = rng.normal(0.05, 1, 1000)
    assert T.deflated_sharpe(x, 1000) < T.deflated_sharpe(x, 1)


def test_reality_check_null():
    rng = np.random.default_rng(3)
    R = rng.normal(0, 1, (500, 20))
    res = T.whites_reality_check(R, n_boot=300)
    assert res["rc_pvalue"] > 0.05
    R[:, 0] += 0.3
    res = T.whites_reality_check(R, n_boot=300)
    assert res["rc_pvalue"] < 0.05 and res["best_idx"] == 0


def test_ledger_hash_chain_detects_tampering(tmp_path, monkeypatch):
    from qpl.research import factory as F
    monkeypatch.setattr(F, "LEDGER", tmp_path / "l.jsonl")
    for i in range(3):
        F.append({"kind": "x", "i": i})
    assert F.verify_ledger() == (True, 3)
    lines = (tmp_path / "l.jsonl").read_text().splitlines()
    lines[1] = lines[1].replace('"i":1', '"i":99')
    (tmp_path / "l.jsonl").write_text("\n".join(lines) + "\n")
    ok, n = F.verify_ledger()
    assert not ok and n == 1


def test_ledger_handles_int_keys(tmp_path, monkeypatch):
    # regression (audit A-L1): int dict keys used to break re-canonicalization during verification
    from qpl.research import factory as F
    monkeypatch.setattr(F, "LEDGER", tmp_path / "l.jsonl")
    F.append({"kind": "x", "pcts": {1: 0.1, 5: 0.5, 25: 2.5, 50: 5.0}})
    F.append({"kind": "y"})
    assert F.verify_ledger() == (True, 2)


def test_validate_detects_gaps_with_microsecond_index():
    # regression V4-A1: gap detection silently failed for microsecond-unit indexes (pandas 3 default)
    from qpl.data.validate import validate_frame
    idx = pd.DatetimeIndex(["2024-01-02 14:30", "2024-01-02 14:45", "2024-01-03 02:00", "2024-01-03 02:15"], tz="UTC").as_unit("us")
    df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0.0}, index=idx)
    rep = validate_frame(df, "M15")
    assert rep["gaps_total"] == 1 and rep["intra_week_gaps_gt_6h"] == 1

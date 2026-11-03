import pandas as pd
import numpy as np

from qpl.live import futures_cx as FX


def test_daily_weekend_on_monday():
    ix = pd.date_range("2026-10-02 00:00", "2026-10-05 23:00", freq="h")          # Fri .. Mon
    d = FX.daily(pd.Series(1.0, index=ix))
    assert list(d.index) == [pd.Timestamp("2026-10-02"), pd.Timestamp("2026-10-05")] and d.iloc[1] == 72.0


def test_proxy_hourly_costs_and_funding():
    ix = pd.date_range("2026-10-01", periods=3, freq="h")
    px = pd.DataFrame({"BTC": [100.0, 110.0, 110.0], "ETH": [10.0, 10.0, 10.0]}, index=ix)
    pos = pd.DataFrame({"BTC": [0.0, 1.0, 1.0], "ETH": 0.0}, index=ix)
    fund = pd.DataFrame({"BTC": [0.0, 0.0, 0.001], "ETH": 0.0}, index=ix)
    h = FX.proxy_hourly(pos, px, fund, cost=lambda c, p: 0.0001)
    assert np.isclose(h.iloc[1], 0.1 - 0.0001) and np.isclose(h.iloc[2], -0.001)


def test_step_appends_once(tmp_path, monkeypatch):
    monkeypatch.setattr(FX, "OUT", tmp_path / "futcx"); monkeypatch.setattr(FX, "OUT4", tmp_path / "futcx4")
    days = pd.bdate_range("2026-10-01", "2026-10-09")
    cx = {"cx": {str(d.date()): 0.001 for d in days}, "cx_solxrp": {str(d.date()): 0.0005 for d in days}, "last_full_day": "2026-10-08"}
    r1 = FX.step(cx_live=cx); r2 = FX.step(cx_live=cx)
    L = pd.read_csv(tmp_path / "futcx/ledger_hourly.csv")
    assert r1["futcx"]["appended"] > 0 and r2["futcx"]["appended"] == 0 and r1["futcx4"]["appended"] == r1["futcx"]["appended"] and r2["futcx4"]["appended"] == 0 and L["hour"].max() <= "2026-10-08 21:00:00"
    assert "CX" in L.columns and "w CX" in L.columns and L["port"].notna().all()
    L4 = pd.read_csv(tmp_path / "futcx4/ledger_hourly.csv")
    assert np.allclose(L4["CX"] - L["CX"], 0.0005)

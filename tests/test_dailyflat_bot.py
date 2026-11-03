"""Daily-flat index-CFD runner (dry-run): flat windows, session / 14:00 switch, order_check only."""
import json

import pandas as pd

from qpl.bot import runner_dailyflat as R
from qpl.bot.rules import Rules
from tests.test_mt5_bridge import FakeMT5

TJ = {"session": "2026-11-04", "targets_before_14et": {"US500": 0.2, "US100": 0.4, "US2000": 0.0, "US30": 0.0},
      "targets_after_14et": {"US500": 0.25, "US100": 0.45, "US2000": 0.05, "US30": 0.05}}
u = lambda et: pd.Timestamp(et).tz_localize("America/New_York").tz_convert("UTC")


def test_flat_windows_and_sessions():
    assert R.current_targets(TJ, u("2026-11-04 15:56")) == {}                          # flat before the rollover
    assert R.current_targets(TJ, u("2026-11-03 17:30")) == {}                          # maintenance window
    assert R.current_targets(TJ, u("2026-11-03 18:05")) == TJ["targets_before_14et"]   # evening of the previous day = session 11-04
    assert R.current_targets(TJ, u("2026-11-04 09:00")) == TJ["targets_before_14et"]
    assert R.current_targets(TJ, u("2026-11-04 14:10")) == TJ["targets_after_14et"]
    assert R.current_targets(TJ, u("2026-11-04 18:05")) is None                        # next session needs a new file
    assert R.current_targets(TJ, u("2026-11-07 12:00")) == {}                          # Saturday
    assert R.current_targets(dict(TJ, targets_after_14et=None), u("2026-11-04 14:10")) == TJ["targets_before_14et"]


def test_one_pass_dry_run(tmp_path):
    mt5 = FakeMT5(); mt5.syms["US500.cash"] = (1.0, 0.1, 0.1, 6000.0)
    p = tmp_path / "t.json"; p.write_text(json.dumps(TJ)); rules = Rules(initial_balance=100_000.0, band_usd=200.0, min_order_usd=50.0)
    r = R.one_pass(mt5, p, 1.0, rules, tmp_path / "st", now=u("2026-11-04 10:00"))
    assert mt5.sent == [] and r["orders"] == 2                                         # US500 + US100 (US2000 / US30 zero)
    st = json.loads((tmp_path / "st/state.json").read_text()); assert set(st["positions"]) == {"US500", "US100"}
    r2 = R.one_pass(mt5, p, 1.0, rules, tmp_path / "st", now=u("2026-11-04 15:57"))
    st = json.loads((tmp_path / "st/state.json").read_text()); assert st["positions"] == {} and r2["orders"] == 2

"""Weekly monitoring report: z-score vs backtest, stale data, bot heartbeat / rejected orders -> alerts; read-only."""
import json

import numpy as np
import pandas as pd

from qpl.hub import weekly as W


def test_weekly_report(tmp_path, monkeypatch):
    pt = tmp_path / "paper_trading"; (pt / "futures").mkdir(parents=True)
    days = pd.bdate_range("2026-10-01", periods=30)
    rng = np.random.default_rng(0); port = rng.normal(-0.004, 0.0035, len(days))      # far below the backtest mean: z < -2
    pd.DataFrame({"hour": [str(d + pd.Timedelta(hours=21)) for d in days], "port": port}).to_csv(pt / "futures/ledger_hourly.csv", index=False)
    bot = tmp_path / "bot_state_x"; bot.mkdir()
    (bot / "status.json").write_text(json.dumps({"last_pass_utc": "2026-11-11 23:58:00", "consecutive_errors": 4, "error": "boom"}))
    (bot / "state.json").write_text(json.dumps({"positions": {"US500": 1000.0}}))
    pd.DataFrame({"time": ["2026-11-10 10:00:00+00:00"], "coin": ["US500"], "usd": [1000.0], "filled_usd": [1000.0], "how": ["market (dry-run: order_check REJECTED x)"],
                  "reason": [""]}).to_csv(bot / "orders_log.csv", index=False)
    monkeypatch.setattr(W, "PT", pt); monkeypatch.setattr(W, "OUT", pt / "reports"); monkeypatch.setattr(W, "ROOT", tmp_path)
    monkeypatch.setenv("QPL_HUB_DB", str(tmp_path / "none.sqlite"))
    before = (pt / "futures/ledger_hourly.csv").read_bytes()
    rep = W.build(pd.Timestamp("2026-11-12 00:00"))
    a = rep["paper"][0]; b = rep["bots"][0]
    assert a["account"] == "futures" and a["z"] < -2 and a["status"] == "ALERT"
    assert b["status"] == "ALERT" and b["rejected_7d"] == 1 and b["gross_usd"] == 1000
    assert len(rep["alerts"]) == 2 and (pt / "reports/weekly_2026-11-12.md").exists()
    assert (pt / "futures/ledger_hourly.csv").read_bytes() == before                       # read-only

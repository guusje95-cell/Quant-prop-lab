"""Propr bridge (dry-run): name mapping, quantity rounding, leverage limits, skips unlisted coins, never posts."""
import json

import pandas as pd

from qpl.bot import venue_propr as P
from qpl.bot.rules import Rules


def test_helpers():
    assert P.hl_name("1000PEPE") == "kPEPE" and P.hl_name("BTC") == "BTC"
    assert P.qty(1234.0, 60000.0, 5) == 0.02056 and P.qty(5.0, 1.0, 0) == 0.0 and P.qty(-25.0, 2.0, 1) == -12.5
    lim = {"defaults": {"crypto": 2}, "overrides": {"BTC": 10}}
    assert P.max_lev(lim, "BTC") == 10 and P.max_lev(lim, "DOGE") == 2


def test_dry_run_pass(tmp_path):
    meta = {"BTC": {"sz": 5, "px": 60000.0}, "ETH": {"sz": 4, "px": 3000.0}, "kPEPE": {"sz": 0, "px": 0.01}}
    lim = {"defaults": {"crypto": 2}, "overrides": {"BTC": 10, "ETH": 10}}
    b = {"for_hour_utc": "2026-11-03 10:00:00", "made_at_utc": "2026-11-03 10:05:00", "equity": 200000.0, "risk": 2.0,
         "target_notional_usd": {"BTC": 400000.0, "ETH": -100000.0, "1000PEPE": -2000.0, "NOTHL": -3000.0},
         "by_sleeve_usd": {"1000PEPE": {"listing short": -2000.0}, "NOTHL": {"venue listing short": -3000.0}}, "lowcap_sleeves": ["listing short", "venue listing short"]}
    bp = tmp_path / "b.json"; bp.write_text(json.dumps(b))
    r = P.one_pass(None, meta, lim, bp, Rules(initial_balance=100_000.0), tmp_path / "st", now=pd.Timestamp("2026-11-03 10:10", tz="UTC"))
    st = json.loads((tmp_path / "st/state.json").read_text())["positions"]
    assert r["skipped"] == 1 and "NOTHL" not in st                                        # not listed on Hyperliquid
    assert abs(st["BTC"]) <= 10 * 100_000 * 0.95 + 1 and abs(st["BTC"] - 100_000) < 100      # risk 1.0 on a $100k account: 400k x 0.25
    assert st["kPEPE" if "kPEPE" in st else "1000PEPE"] < 0

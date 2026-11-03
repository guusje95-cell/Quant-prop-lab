"""Daily-flat variant of the futures paper run (DF-1, 2026-11-03): the SAME frozen-ledger trader (scripts/futures_paper.py, unchanged)
on EXACT daily-flat bars (scripts/v99/dailyflat.py: flat in the 16:00 ET bar, session-open gaps not earned, one extra round trip per
held day) -> paper_trading/futuresdf/ledger_hourly.csv. This is the book for flat-by-close firms (Topstep / Lucid / Tradeify / Apex /
MFFU). Simulation only: no orders, no broker.

    python scripts/futures_paper_dailyflat.py"""
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99")); sys.path.insert(0, str(ROOT / "src"))
os.environ["QPL_DAILY_FLAT"] = "1"
os.environ.setdefault("QPL_FUT_PAPER_OUT", str(ROOT / "paper_trading/futuresdf"))
if "--check" not in sys.argv:
    from qpl.live import databento_update as DU
    os.environ["QPL_DATABENTO"] = str(DU.merged_dir())
import dailyflat  # noqa: E402

dailyflat.patch()
runpy.run_path(str(ROOT / "scripts/futures_paper.py"), run_name="__main__")

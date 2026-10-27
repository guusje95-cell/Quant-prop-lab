"""v9.8 freeze guard. `python scripts/v99/check_v98_freeze.py --write` records sha256 of every file the v98 paper trader (and its
live feeds, launchers, configs, caches and research data) uses into config/v98_freeze.json; without --write it verifies them and
exits 1 on any change. Research for v9.9 lives in scripts/v99 and research/v99 and must never change these files."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
CODE = ["scripts/paper_v5.py", "scripts/event_live.py", "scripts/listing_live.py", "scripts/basket_live.py", "scripts/crypto_sleeves.py",
        "scripts/ridge_live.py", "scripts/alt_kimchi.py", "scripts/gen57_cascade_hourly.py", "scripts/cfd_book.py", "scripts/paper_report.py",
        "src/qpl/lab/binance_pack.py", "src/qpl/lab/extra_pack.py", "src/qpl/lab/data.py", "src/qpl/lab/propfirms.py", "src/qpl/data/coinmetrics.py",
        "src/qpl/live/binance_public.py", "src/qpl/live/binance_announcements.py", "src/qpl/live/bybit_listings.py", "src/qpl/live/coinbase_public.py",
        "src/qpl/live/ml_feeds.py", "src/qpl/bot/planner.py", "src/qpl/bot/rules.py", "src/qpl/bot/runner.py",
        "config/paper_v98.json", "config/listing_crowding.json", "config/tradfi_perps.json", "config/paper_monitor.json",
        "results/cache_v98_final.parquet", "results/paper_sleeve_sd.json",
        "paper_v98_start.bat", "paper_v98_once.bat", "paper_v98_status.bat", "paper_v98_share.bat"]
DATA_DIRS = ["research_data/binance", "research_data/binance_extra", "research_data/binance_pit", "research_data/binance_announcements",
             "research_data/bybit_listings", "research_data/coinbase", "research_data/upbit", "data/processed"]
F = ROOT / "config/v98_freeze.json"
def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest() if (ROOT / p).exists() else None
def tree(d):                                           # git tree hash of a tracked data directory (None if not tracked)
    r = subprocess.run(["git", "rev-parse", f"HEAD:{d}"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() or None
def state():
    return {"files": {p: sha(p) for p in CODE}, "data_trees_at_HEAD": {d: tree(d) for d in DATA_DIRS}}
if "--write" in sys.argv:
    s = state(); s["frozen_at_commit"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    F.write_text(json.dumps(s, indent=1)); print("written", F)
else:
    ref = json.loads(F.read_text()); now = state(); bad = [p for p in CODE if ref["files"].get(p) != now["files"][p]]
    bad += [d for d in DATA_DIRS if ref["data_trees_at_HEAD"].get(d) != now["data_trees_at_HEAD"][d]]
    print("v98 FREEZE OK" if not bad else f"v98 FREEZE BROKEN: {bad}"); sys.exit(1 if bad else 0)

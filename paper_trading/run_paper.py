"""Paper-trading entry point.

  python paper_trading/run_paper.py --replay data/processed/topstepx/MNQ_15min.parquet
  python paper_trading/run_paper.py --csv my_bars.csv          # columns: datetime(UTC ISO),open,high,low,close,volume

Live use: append each COMPLETED 15-minute MNQ bar (UTC open-time stamp) to a CSV from your data
feed and re-run with --csv --resume, or call PaperTrader.on_bar() from your feed callback.
This program never sends orders anywhere.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.execution.paper import PaperConfig, replay  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", help="parquet of UTC bars")
    ap.add_argument("--csv", help="csv of UTC bars")
    ap.add_argument("--config", default=str(ROOT / "config" / "paper_trading.json"))
    a = ap.parse_args()
    cfg_d = {k: v for k, v in json.loads(Path(a.config).read_text()).items() if not k.startswith("_")}
    cfg = PaperConfig(**cfg_d)
    if a.replay:
        df = pd.read_parquet(a.replay)
    else:
        df = pd.read_csv(a.csv)
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        df = df.set_index("datetime").sort_index()
    pt = replay(df, cfg, ROOT / "paper_trading" / "logs")
    s = pt.summary()
    pd.DataFrame(pt.trades).to_csv(ROOT / "paper_trading" / "logs" / "last_trades.csv", index=False)
    pd.DataFrame(pt.days).to_csv(ROOT / "paper_trading" / "logs" / "last_days.csv", index=False)
    print(json.dumps(s, indent=1, default=str))


if __name__ == "__main__":
    main()

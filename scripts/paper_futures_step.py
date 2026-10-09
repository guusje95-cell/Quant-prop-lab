"""Step the F9 futures paper book (simulation only). Usage:
  python scripts/paper_futures_step.py --data-dir /path/to/pysystemtrade-format/futures --capital 1000000 [--state paper_trading/f9_state.json]
The data directory must contain adjusted_prices_csv/, multiple_prices_csv/, fx_prices_csv/ and csvconfig/ in pysystemtrade format,
updated by the user from a licensed source. Nothing is downloaded and no order is sent anywhere."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.data import futures_panel as FP
from qpl.execution.paper_futures import FuturesPaperBook
ap = argparse.ArgumentParser(); ap.add_argument("--data-dir", required=True); ap.add_argument("--capital", type=float, default=1e6)
ap.add_argument("--state", default="paper_trading/f9_state.json"); a = ap.parse_args()
FP.set_source(a.data_dir)
P = FP.build(force=True); U, _ = FP.universe(P)
members = FP.smallest_members(P, U) if a.capital < 5e6 else {k: k for k in U}
Path(a.state).parent.mkdir(parents=True, exist_ok=True)
print(json.dumps(FuturesPaperBook(a.capital, a.state).step(P, U, members), indent=1, default=str))

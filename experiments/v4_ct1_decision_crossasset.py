"""Record the CT1 grade after the single-use cross-asset confirmation (no re-tuning)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.research import factory as F, registry as R
ROOT = Path(__file__).resolve().parents[1]
x = json.loads((ROOT / "results/v4_ct1_crossasset.json").read_text())
reason = ("Grade kept at PAPER_TRADING_CANDIDATE (personal-account research track; NOT prop-compatible) with REDUCED confidence. "
          f"Cross-asset confirmation: ETH 2018-23 PASS (net {x['A_ETH']['sharpe']:.2f}, resid {x['A_ETH']['residual_sharpe']:.2f}, maxDD {x['A_ETH']['max_dd']:.0%}); "
          f"21 Binance perps 2025-12..2026-09 FAIL (portfolio net {x['B_PERPS']['sharpe']:.2f}, resid {x['B_PERPS']['residual_sharpe']:.2f}; ~9 months, daily mark proxy, +1d lag). "
          "Interpretation: trend edge not shown to generalise to the recent alt-coin cross-section; BTC/ETH-only deployment, no parameter change, "
          "recent-period weakness (BTC holdout 0.34, perps ~0) is consistent with decay.")
R.set_verdict("CT1_TREND_ENSEMBLE", "PAPER_TRADING_CANDIDATE", reason)
F.append({"kind": "decision", "hypothesis_id": "CT1_TREND_ENSEMBLE", "verdict": "PAPER_TRADING_CANDIDATE", "reason": reason,
          "evidence": {"crossasset": "results/v4_ct1_crossasset.json", "confidence": "reduced"}})
print(reason)

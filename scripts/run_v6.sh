#!/usr/bin/env bash
# Reproduce every V6 experiment. Single-use looks re-run reproduce the recorded numbers and are tagged in the ledger.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
export QPL_LEDGER_TAG="${QPL_LEDGER_TAG:-repro}"
python3 experiments/v6_ct1_decay.py
python3 experiments/v6_futures_gen13.py
python3 experiments/v6_futures_audit.py
python3 experiments/v6_futures_gen14.py
python3 experiments/v6_gen15_regime.py
python3 experiments/v6_gen15_ml.py
python3 experiments/v6_futures_stats.py
python3 experiments/v6_portfolio.py
python3 experiments/v6_gen16_crypto_xs.py
python3 experiments/v6_f9_record.py
python3 scripts/v6_registry.py
python3 -c "from qpl.research import factory as F; print('ledger', F.verify_ledger())"

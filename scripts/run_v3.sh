#!/usr/bin/env bash
# Reproduce every v3 experiment. Holdout/OOS scripts are single-use research decisions: re-running
# them reproduces the recorded result and is labelled in the ledger via QPL_LEDGER_TAG.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
export QPL_LEDGER_TAG="${QPL_LEDGER_TAG:-repro}"
(cd experiments && python3 audit_v1.py)
python3 experiments/v3_holdout_crossmarket.py
python3 experiments/v3_gen7_campaign.py
python3 experiments/v3_gen8_stat.py
python3 experiments/v3_v7_diagnostics.py
python3 experiments/v3_regime_filters.py
python3 experiments/v3_sizing.py
python3 experiments/v3_pbo.py
python3 experiments/v3_decay_diagnostics.py
python3 experiments/v3_gen9_fx.py
python3 experiments/v3_v11_gold.py dev
python3 experiments/v3_v11_gold.py oos
python3 experiments/v3_portfolios.py
python3 -c "from qpl.research import factory as F; print('ledger', F.verify_ledger())"

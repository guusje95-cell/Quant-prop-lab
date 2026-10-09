#!/usr/bin/env bash
# Reproduce every V4 experiment. OOS/holdout looks are single-use research decisions: re-running them reproduces the
# recorded numbers and is labelled in the ledger via QPL_LEDGER_TAG (never counted as a new look).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
export QPL_LEDGER_TAG="${QPL_LEDGER_TAG:-repro}"
python3 -c "from qpl.data import crypto as CD; CD.write_inventory()"           # data inventory + validation
python3 experiments/v4_crypto_gen10.py                                           # BTC directional screen (TRAIN+VAL)
python3 experiments/v4_ct1_evaluate.py                                           # CT1 dev/OOS/holdout (no new records; checks stored numbers)
python3 experiments/v4_ct1_crossasset.py                                         # ETH + 21 perps confirmation
python3 experiments/v4_gen11.py                                                  # funding / carry / calendar / regime / XS momentum
python3 experiments/v4_gen12.py                                                  # ETH-BTC relative value, 4h trend variant
python3 experiments/v4_audit_c1_correction.py                                    # realized-label corrections
python3 experiments/v4_ct1_risk.py                                               # sizing, Kelly, DSR, stress
python3 experiments/v4_ct1_prop_crypto.py                                        # evaluation-rule simulation (UNCERTAIN rules)
python3 experiments/v4_portfolio.py                                              # nested BTC+ETH portfolio
python3 experiments/v4_paper_crypto_replay.py                                    # paper stack replay + reconciliation
python3 -m qpl.reporting.report_v4                                               # reports/v4_research_report.html
python3 -c "from qpl.research import factory as F; print('ledger', F.verify_ledger())"

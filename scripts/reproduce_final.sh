#!/usr/bin/env bash
# Reproduce the final analysis of the frozen candidate (H3 noise-area, NQ/MNQ)
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
python3 experiments/candidate_eval.py h3
python3 experiments/h3_falsification.py
python3 experiments/prop_eval.py h3
python3 experiments/prop_eval.py h3_ftmo
python3 experiments/final_test.py calibrate
python3 experiments/final_test.py test
python3 experiments/prop_scenarios.py

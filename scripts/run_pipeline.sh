#!/usr/bin/env bash
# Full research pipeline: pinned data -> validation -> every research generation (TRAIN/VALIDATION)
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
python3 -m qpl.data.fetch
python3 -m qpl.data.validate
python3 experiments/gen1_screen.py            # gen1: historical tick costs
python3 experiments/gen1_screen.py --norm     # gen2: deployment-normalized costs
python3 experiments/gen2_neighborhood.py      # gen2: neighbourhoods on TRAIN+VALIDATION
python3 experiments/h4_candidate_eval.py      # gen3: frozen H4 (rejected OOS)
python3 experiments/gen4_crossasset.py        # gen4: H6 cross-asset
python3 experiments/gen5_diversifiers.py      # gen5: H7, H8
python3 experiments/gen6_misc.py              # gen6: H9, H10
bash scripts/reproduce_final.sh

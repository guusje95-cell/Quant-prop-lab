#!/usr/bin/env bash
# Extra (small): hourly perp premium index (basis) for the 20 coins. Run after get_binance_data.sh, then push research_data.
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && . .venv/bin/activate
PYTHONPATH=src python -m qpl.lab.binance_vision premium
echo "Done. Now: git add research_data && git commit -m 'Binance premium index' && git push"

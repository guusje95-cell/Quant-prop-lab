#!/usr/bin/env bash
# Paper trading v5 (Linux/macOS): ./paper_v5.sh loop | run | status | reconcile | selftest
cd "$(dirname "$0")"; [ -f .venv/bin/activate ] && . .venv/bin/activate
PYTHONPATH="$PWD/src" python scripts/paper_v5.py "${1:-loop}"

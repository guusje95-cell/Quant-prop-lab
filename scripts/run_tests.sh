#!/usr/bin/env bash
# Automated tests: engine, accounting, prop rules, data/calendar, statistics, look-ahead, paper parity
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pytest -q

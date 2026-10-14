#!/usr/bin/env bash
# Backtest Lab launcher for macOS / Linux:  bash run_lab.sh
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  . .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt -r requirements-lab.txt
else
  . .venv/bin/activate
fi
export PYTHONPATH="$PWD/src"
[ -f data/lab/crypto_majors_1d.parquet ] || python -m qpl.lab.setup_data
streamlit run app/lab.py

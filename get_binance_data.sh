#!/usr/bin/env bash
# Downloads free Binance futures data (1-minute candles, open interest / long-short ratios, funding) for 20 coins.
cd "$(dirname "$0")"; [ -f .venv/bin/activate ] && . .venv/bin/activate
PYTHONPATH=src python -m qpl.lab.binance_vision all

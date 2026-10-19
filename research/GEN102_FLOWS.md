# Gen102: more demand-flow signals (2026-10-19)

- **Protocol:** `config/gen102_protocol.json`, registered **before the data was downloaded**. 5 trials.
- **Data:** downloaded by the user with `get_more_data.bat`.
- **Script:** `scripts/gen102_flows.py`.
- **Baseline:** the current CFD book (C\*, Weiss, bounce, Coinbase premium), Sharpe 1.854.

| Test | DEV 20-22 | TEST 23-24 | HOLD 25-26 | Corr C\* | Book after | Verdict |
|---|---|---|---|---|---|---|
| P1 Coinbase premium on 9 CFD altcoins | -0.34 | 0.40 | -0.55 | -0.15 | 1.24 | rejected |
| **P2 kimchi premium momentum** (Upbit KRW vs Binance, z > 1 long / < -1 short, 1 day) | **0.40** | **0.80** | **1.29** | 0.00 | 1.70 | rejected: passes alone, lowers the book |
| P2b kimchi contrarian (variant) | -0.82 | -1.49 | -1.93 | | 1.26 | variant: strongly negative, which confirms the momentum direction |
| P3 Fear & Greed <= 20 -> long 3 days | 0.02 | 0.23 | -0.24 | | 1.67 | rejected |
| P4 Bitstamp replication of the Coinbase premium (check) | 0.25 | 1.25 | 0.36 | | | **replicates** (corr 0.93 with the Coinbase sleeve) |

**Kimchi premium level:**
- BTC and ETH median +133 bp; 1-99% range -300 to +1,220 bp.
- 2,465 days of data.

## What P4 changes in how the Coinbase premium is read

- Bitstamp, a different USD venue, gives almost the same signal: correlation 0.93.
- So the "Coinbase premium" is mostly the **USD-spot-vs-USDT-perp basis** (USDT/USD rate plus the perp basis), not Coinbase-specific US demand.
- The effect is real and venue-independent, which is good for robustness. Its live implementation can use any USD spot venue.

## Note for a later pre-registration (not tested here)

- The kimchi momentum signal is strong on its own (HOLD 1.29) and uncorrelated with C\*.
- It lowers the book because equal-risk weighting adds a second demand sleeve next to the Coinbase premium.
- A single **"demand composite"** sleeve (average of the Coinbase and kimchi z-scores) is a reasonable next hypothesis.
- It must be registered as a new trial, not adopted from this table.

# Gen109: machine learning in the crypto-firm book (2026-10-19)

- **Protocol:** `config/gen109_protocol.json`, registered before any number. 2 trials.
- **Scripts:** `scripts/gen109_ml_v6.py` and `scripts/gen109_check.py`.

| Test | DEV 2021-22 | TEST 23-24 | HOLD 25-26 | Corr C\* | v6 2022-26 (2.458) | v6 TEST / HOLD (3.435 / 1.901) | Verdict |
|---|---|---|---|---|---|---|---|
| **X1 Gen108 ridge (16 point-in-time features, walk-forward) in v6, perp costs** | **0.13** | **1.28** | **1.36** | 0.19 | **2.534** | **3.494 / 2.240** | **PASSES every rule** |
| X2 cross-sectional ridge, 20 coins, weekly | 0.03 | -1.50 | 0.96 | -0.24 | 2.419 | 3.003 / 2.125 | rejected |

## X1 robustness (descriptive)

| Check | DEV | TEST | HOLD | v6 |
|---|---|---|---|---|
| base | 0.13 | 1.28 | 1.36 | 2.53 |
| alpha 1 / alpha 100 | 0.12 / 0.01 | 1.28 / 1.33 | 1.36 / 1.32 | 2.53 / 2.54 |
| quarterly refit | 0.17 | 1.33 | 1.31 | 2.53 |
| without the Coinbase/kimchi z features | -0.18 | 0.45 | 0.97 | 2.41 |
| without the derivatives features | 0.03 | 1.16 | 0.49 | 2.44 |
| price features only | -0.10 | 0.47 | 0.07 | 2.32 |
| BTC only / ETH only | -0.20 / 0.31 | 1.46 / 0.93 | 1.71 / 0.91 | 2.62 / 2.46 |
| 2x costs | -0.03 | 1.03 | 1.06 | 2.45 |
| placebo (predictions shuffled in 30-day blocks, 100 runs) | | mean of TEST and HOLD -0.05, 95th percentile 0.79; actual 1.32, **p < 0.01** | | |

**Reading the checks**
- Insensitive to the model settings.
- Clearly better than chance.
- The value comes from the flow features (Coinbase / Korean premiums), plus funding / OI / taker flow, not from price patterns.
- **Weak point:** DEV 2021-22 is close to zero, and slightly negative at 2x costs.
- **Not counted:** the "executed late" rows of the check script only shift the P&L stream and are not a real delay test.

## Decision: ADOPTED as the candidate for v7 (v6 + ML sleeve)

- **v6 2022-26:** 2.46 -> **2.53**.
- **TEST:** 3.44 -> 3.49.
- **HOLD:** 1.90 -> 2.24.

**Live use needs feeds the paper trader does not have yet:**
- Coinbase: already in 'bf';
- Upbit KRW plus Yahoo USD/KRW, dated by London day;
- Deribit DVOL (public);
- the monthly refit.

v6 paper trading stays as it is until v7 is built and passes its own no-look-ahead self-test.

**BrightFunded book:** the same ML sleeve failed the book-TEST rule there by 0.03 (Gen108). It is not added to 'bf'.

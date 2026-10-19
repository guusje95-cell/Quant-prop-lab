# Gen88 + Gen101: the Coinbase premium (2026-10-19)

- **Protocols:**
  - `config/gen88_protocol.json`, registered 2026-10-18, **before the data was downloaded**. 3 trials.
  - `config/gen101_protocol.json`, 1 trial.
- **Data:** Coinbase BTC-USD / ETH-USD hourly, downloaded by the user on 2026-10-19. 59,144 matched hours, 2020-01..2026-09.
- **Scripts:** `scripts/gen88_coinbase.py`, `scripts/gen88_check.py`, `scripts/gen88_books.py`, `scripts/gen101_v6_premium.py`.

## Signal

- **Premium:** Coinbase close / Binance perp close - 1. Median +3 bp; 1-99% range about -25 to +30 bp.
- **z-score:** the 24h mean of the premium, compared with its 30-day mean and spread.
- **Q1 rule:** at 00:00 UTC, long the coin when z > +1, short when z < -1, otherwise flat. Hold 24h; BTC and ETH 0.5 each.

## Results (CFD costs: 5 bp, swap 3.3)

| Test | DEV 20-22 | TEST 23-24 | HOLD 25-26 | Corr C\* | Gen85 book 1.618 -> | Verdict |
|---|---|---|---|---|---|---|
| **Q1 premium momentum z > 1** | **0.57** | **1.12** | **0.50** | -0.04 | **1.849** | **PASSED** |
| Q3 variant z > 0.5 | 0.61 | 0.97 | 0.35 | -0.05 | 2.007 | variant (also positive) |
| Q2 C\* scaled by the BTC premium | 2.23 (C\* 2.21) | 2.20 (2.32) | 0.48 (0.50) | | 1.514 | rejected |

## Checks on Q1 (descriptive)

**Timestamp alignment:**
- Hourly returns Coinbase vs Binance correlate 0.998 at lag 0, and -0.002 / -0.007 at lag ±1h.
- So the premium is not a clock artefact.

**Variants:**

| Check | DEV | TEST | HOLD | 2020-26 |
|---|---|---|---|---|
| base | 0.57 | 1.12 | 0.50 | 0.67 |
| threshold 0.75 / 1.25 / 1.5 | 0.60 / 0.41 / 0.59 | 0.89 / 1.48 / 1.47 | 0.21 / 0.43 / 0.23 | 0.56 / 0.66 / 0.69 |
| hold 2 / 3 days | | | -0.04 / -0.21 | 0.61 / 0.35 (short-lived signal) |
| BTC only / ETH only | | | | 0.39 / 0.78 |
| long leg / short leg | 1.19 / -0.50 | 1.70 / -0.02 | -0.14 / 0.75 | 0.98 / -0.04 |
| entry 1h / 4h / 12h late | | | | 0.64 / 0.65 / 0.49 |
| 2x spread / swap-free / swap 6.6 | | | | 0.55 / 0.79 / 0.55 |
| **placebo (30-day blocks shuffled, 200 runs)** | | | | mean -0.17, 95th percentile 0.44 -> **p = 0.01** |

**Weak points:**
- HOLD sits right at the 0.5 bar and varies with the threshold (0.21-0.50).
- The edge is in ETH more than BTC.
- The long and short legs work in different periods.

## Books (2022-26, 15% vol)

| Book | Sharpe | TEST | HOLD | Max DD | Positive months |
|---|---|---|---|---|---|
| CFD book Gen90 (C\* + Weiss + bounce) | 1.80 | 3.09 | 1.31 | -11.8% | 56% |
| **CFD book + Coinbase premium** | **1.85** | 3.00 | 1.33 | -12.3% | 63% |
| swap-free book Gen90 | 2.07 | 3.41 | 1.36 | -10.0% | 70% |
| **swap-free + Coinbase premium** | **2.15** | 3.36 | 1.42 | -10.6% | 68% |

## Gen101: crypto-firm v6 at perp costs

- **Q1 alone:** DEV 0.73, TEST 1.30, HOLD 0.66, corr C\* -0.04. It **passes** the crypto rule.
- **v6 2.458 -> 2.469:** a negligible gain, and v6 HOLD falls 1.90 -> 1.79.
- **Decision:** v6 paper trading stays as it is. The premium is not added (gain within noise).

## Decision

- **CFD route:** the Coinbase premium is adopted as the 4th sleeve of the CFD books. Normal 1.80 -> 1.85, swap-free 2.07 -> 2.15.
- **Live use needs a Coinbase hourly feed.** It is public and needs no key, but it is not yet in the paper trader.

# Gen108: walk-forward machine learning (2026-10-19)

- **Protocol:** `config/gen108_protocol.json`, registered before any number. 2 trials.
- **Script:** `scripts/gen108_ml.py`.
- **Predictions:** `results/gen108_preds.parquet`.

**Setup**
- **Data:** BTC and ETH pooled, daily, 16 point-in-time features (returns, volatility, funding, premium, open interest, taker imbalance, Coinbase z, kimchi z with strict FX, DVOL change, stablecoin growth).
- **Walk-forward:** refit every month on past data only. Predictions from 2021-01.
- **Execution:** BrightFunded costs.

| Model | DEV 2021-22 | TEST 23-24 | HOLD 25-26 | Hit rate | Corr C\* | Book 2022-26 (2.252) | Book TEST / HOLD (3.45 / 1.55) | Verdict |
|---|---|---|---|---|---|---|---|---|
| **ML1 ridge** | **0.27** | **1.49** | **1.49** | 51.0% | 0.18 | 2.283 | **3.42** / 1.95 | not adopted: book TEST falls by 0.03 |
| ML2 gradient boosting | 0.48 | -0.40 | 1.32 | 51.9% | 0.12 | 2.217 | 3.06 / 1.86 | rejected |

**Ridge coefficients** (fit on 2020-03..2024-12, bp of next-day return per 1 sd of the feature):

| Effect | Features |
|---|---|
| Positive | taker imbalance +35; Coinbase z +25; 30-day return +22; premium +16; funding today +13; OI 1d +12; kimchi z +10 |
| Negative | 1-day return -59 (short-term reversal); 7-day funding -21 (crowding); OI 7d -10; stablecoin growth -9 |

These are interpretable effects, not noise fitting.

## Reading

- **The linear model passes every sleeve criterion** (0.27 / 1.49 / 1.49, walk-forward, so no in-sample fit). It raises the book and book HOLD (1.55 -> 1.95).
- **It fails only the "book TEST not lower" rule,** by 0.03 (3.45 -> 3.42).
- The same thing blocked the demand composite (Gen105). The book's 2023-24 Sharpe of 3.45 is so high that any extra sleeve with a lower Sharpe dilutes it slightly.
- **Changing the rule now, after seeing these results, would be fitting the rules to the answer, so it stays.**
- **Ridge ML goes to the watchlist with the demand composite.** Both are candidates to judge on fresh paper-trading data.
- Any future relaxation of the book criterion must be registered **before** the next test, not applied to this one.

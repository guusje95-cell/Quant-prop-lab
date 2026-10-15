# Crypto portfolio + Gen61 (2026-10-15)

## Gen61: remaining crypto ideas (pre-registered in `config/gen61_protocol.json`)

| Test | DEV | TEST | HOLD | 2023+ | corr C* | Verdict |
|---|---|---|---|---|---|---|
| G1 crowding overlay on C* | | | | 1.53 vs 1.58 | | rejected (lower Sharpe and Calmar) |
| G2 funding-settlement window (maker) | -1.23 | -0.30 | -0.62 | -0.42 | -0.16 | rejected |
| **G4 premium carry XS (7d average premium, weekly)** | 0.92 | 0.79 | 1.18 | **0.95** | -0.07 | **PASSED** |
| G5 bear short sleeve BTC+ETH | 0.11 | -0.57 | 0.44 | 0.02 | -0.04 | rejected (2022: only +3%) |
| G12 Monday-anchored intraday trend | 2.20 | 2.50 | -2.96 | -0.08 | 0.09 | rejected (collapsed in 2025-26) |

**G4 robustness** (Sharpe 2023+):
- 2x costs: 0.81.
- Neighbouring settings: look-back 3d 0.91, 14d 1.07; hold 1d 0.82, 14d 0.62.
- 2022 was about 0.
- Correlation with the funding-carry near-miss is 0.66 (same idea, better measured), so premium carry replaces funding carry.

## Portfolio (descriptive)

**Construction:**
- C* + BTC leads (perps, real funding), premium carry, liquidation-cascade buy (max 3 open) and ETH 21-23 UTC (maker).
- Each sleeve is scaled to 10% vol, they are equal-weighted, and the total is scaled to 15% vol.
- Built from the hourly path.
- Script: `scripts/gen58_crypto_portfolio.py`. Chart: `results/gen58_crypto_portfolio.png`.

| | Sharpe 2022-26 | Sharpe 2023+ | Positive months 2022-26 | Max DD | 2022 | 2023 | 2024 | 2025 | 2026 YTD |
|---|---|---|---|---|---|---|---|---|---|
| C* alone | 1.28 | 1.58 | 42% | -15.7% | -6% | +45% | +54% | +2% | +10% |
| 3 sleeves (C*, premium carry, cascade) | **1.55** | 1.97 | 61% | -16.5% | -5% | +41% | +57% | +16% | +18% |
| 4 sleeves (+ ETH evening) | 1.41 | **2.15** | 63% | -21.0% | -19% | +35% | +67% | +27% | +12% |

Correlations with C*, 2022+: premium carry -0.07, cascade 0.23, ETH evening 0.17.

**2022 (crypto bear market) hurt every crypto sleeve.** ETH evening was the worst (Sharpe -1.8 in 2022), which is why the 3-sleeve version is more robust over 2022-26. Crypto sleeves share the crypto regime; real diversification needs non-crypto strategies (Dukascopy, Databento).

## Prop simulation

**Setup:** hourly path 2022-01 to 2026-09, 1 account of $100k, up to 5 challenges, 24 months. The challenge runs at 1.0x (15% vol). Exchange costs are used, not each firm's own.

Net profit per account over 2 years (average / unlucky 10%) and months with income:

| Firm | C* alone (funded 0.4x) | Portfolio (funded 0.4x) | Portfolio (funded 0.6x) |
|---|---|---|---|
| FTMO 2-Step | $12.9k / $4.5k, 22% | $15.1k / $6.4k, 44% | $22.9k / $9.9k, 44% |
| HyroTrader 1-Step | $10.7k / $6.6k, 19% | $17.4k / $8.6k, 46% | $22.9k / $13.1k, 37% |
| FundedNext Stellar | $13.0k / $5.5k, 24% | $15.5k / $6.7k, 45% | $23.5k / $10.4k, 45% |
| CFT 1-Phase | $8.8k / $5.6k, 18% | $14.2k / $5.7k, 48% | $17.3k / $6.9k, 31% |

- **Pass rate:** 44-48% for C* alone, 61-71% for the portfolio (2-steps).
- **Chance of profit:** 98-100%.
- **Months with income roughly double**, from about 20% to about 45%, and net profit rises 20-80%.

**Caveat:** this is descriptive. Three of the four sleeves were chosen on 2023+ data among many tests, and only premium carry passed every pre-registered criterion. Next step: forward-test in paper trading, and add non-crypto sleeves.

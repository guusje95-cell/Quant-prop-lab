# Gen74: the crypto portfolio as CFDs at CFD prop firms

- **Protocol:** `config/gen74_protocol.json`.
- **Script:** `scripts/gen74_crypto_cfd.py`.
- **Results:** `results/gen74_*.csv`.
- **Setup:**
  - Binance prices, 11 coins commonly offered as CFDs.
  - CFD spread of 5 bp (BTC/ETH) / 10 bp (others) per side.
  - No funding.
  - Swap on |notional| held over 22:00 UTC, three levels: 0 / 3.3 (base) / 6.6 bp per day.
- **Trials added:** 5.

## Sleeves at base costs (swap 3.3 bp/day)
| Sleeve | 2020-22 | 2023-24 | 2025-26 | 2022-26 | In the CFD portfolio? |
|---|---|---|---|---|---|
| C* | 2.17 | 2.25 | 0.35 | 1.17 | yes |
| Weiss expiry | 0.46 | 1.64 | 0.63 | 1.11 | yes (intraday, no swap) |
| trend 4h | 0.81 | 1.27 | 0.24 | 0.70 | no (2025-26 0.24 < 0.3) |
| cascade (11 CFD coins) | -0.14 | 1.32 | -0.58 | 0.33 | no (negative 2025-26, even with zero swap) |
| premium carry (price only) | -0.08 | 0.60 | -0.16 | 0.10 | no (the edge was the funding it collects) |

## CFD portfolio = C* + Weiss expiry (Gen72 point-in-time equal risk, at 15% vol)
| Costs | Sharpe 2022-26 | CAGR | Max DD | Positive months | 2022 | 2025 |
|---|---|---|---|---|---|---|
| swap 0 | 1.60 | 25.6% | -15.5% | 49% | -8.6% | +13.0% |
| **swap 3.3 (base)** | **1.50** | **23.8%** | **-16.1%** | **49%** | -9.7% | +11.7% |
| swap 6.6 | 1.40 | 22.0% | -16.8% | 49% | -10.8% | +10.3% |
| swap 3.3, 2x spread | 1.17 | 17.8% | -18.3% | 47% | -13.2% | +7.3% |

## Prop: $100k, 2 years, bootstrap, daily stop at 50% of the firm's daily limit
| Firm | Risk | Pass | Days to pass | Mean net | Unlucky 10% | P(profit) |
|---|---|---|---|---|---|---|
| FTMO 2-Step | 1.0 / 0.6 | 73% | 157 | $14.3k | $0 | 90% |
| FundedNext Stellar 2-Step | 1.0 / 0.6 | 81% | 157 | $15.1k | $1.4k | 92% |
| BrightFunded 2-Step Classic | 1.0 / 0.6 | 73% | 157 | $14.2k | $0 | 90% |
| (same firms at swap 6.6) | 1.0 / 0.6 | 70-77% | 152-158 | $13.2-14.1k | about -$0.5k | 88-90% |

At 0.75 / 0.4 the mean net is $8-9k, with an unlucky 10% of about minus the fee.

## Verdict
- **The CFD route works, but it is clearly weaker than the crypto-firm route.** Compare v5 at HyroTrader 1-Step: Sharpe 2.25, $26.4k mean net, unlucky 10% $12.0k, P(profit) 99.6%.
- **Why weaker:** only 2 sleeves survive CFD costs; it has fewer positive months (49% vs 72%), slower challenges (about 5 months vs 3) and a losing 2022.
- **Use at CFD firms only as a second channel,** after the crypto firms. To make it a strong channel, CFD firms need their own uncorrelated, non-crypto strategies.
- **Gen73 found none so far.** Next to test: FX fix, multi-asset trend (35 CFDs), and BTC/ETH on Dukascopy CFD prices, once the remaining files arrive.
- **The swap is the key unknown.** Check the firm's crypto swap rates on its website before buying. Above about 6.6 bp/day (24%/yr), C* loses most of its 2025-26 edge.

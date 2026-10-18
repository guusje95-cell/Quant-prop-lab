# Gen81-83: improving the CFD book

- **Protocols:** `config/gen81_protocol.json`, `gen82_protocol.json`, `gen83_protocol.json`.
- **Scripts:** `scripts/gen81_cfd_book.py`, `gen82_orb.py`, `gen83_swapfree.py`.

## Gen81: cheaper C* execution and a CFD-native crypto edge (rejected)
- **Rebalance band 0.10 / 0.25 / 0.50 on C*:** C* turns over only about 4.7% of its book per day, so the band changes nothing (2022-26 Sharpe 1.21-1.22 at every band). The band picked on 2020-22 was 0, so nothing is adopted. Trading costs are not what limits the CFD book.
- **CME weekend-gap reversion on BTC/ETH:**
  - 2020-22: -0.86; 2023-24: -1.28; 2025-26: +1.54; 2022-26: -0.36. Rejected.
  - The recent strength follows two negative periods.

## Gen82: 5-minute Opening Range Breakout on US100 / US500 CFDs (rejected)
Zarattini, Barbon & Aziz 2024 rule: first 5-minute bar sets the direction, stop at the bar's other side, 10R target, risk 0.5% per trade.

| | DEV 2018-20 | TEST 2021-23 | HOLD 2024-26 | All | at 2 bp |
|---|---|---|---|---|---|
| US100 (primary) | 0.63 | 0.56 | 0.06 | 0.44 | -0.21 |
| US500 | -0.38 | 0.33 | -0.86 | -0.26 | -1.19 |

- **Trades:** 2,177 on US100. 24% win, 2.4% hit the 10R target.
- **Verdict:** weak and fading on CFD costs. Another candidate for the futures (Databento) test.

## Gen83: swap-free CFD book (for accounts with no overnight swap on crypto)
- **The rule is unchanged from Gen74.** Keep a sleeve if 2023-24 >= 0.5 and 2025-26 >= 0.3, here applied at zero swap.
- **What that keeps:**
  - C*: 2.38 / 0.47;
  - premium carry, price-only: 1.22 / 0.57;
  - trend 4h: 1.47 / 0.42;
  - Weiss: 1.64 / 0.63.
- **The cascade still fails.**
- **Sleeve correlations:** at most 0.35 (C* / trend 4h); all others are about 0.

| 2022-26, 15% vol | Swap-free book (4 sleeves) | Same, 2x spread | Base CFD book (C* + Weiss, swap 3.3/day) |
|---|---|---|---|
| Sharpe | **1.81** | 1.44 | 1.57 |
| CAGR | 29.8% | 22.7% | 25.1% |
| Max DD | **-12.8%** | -14.6% | -16.0% |
| Positive months | **67%** | 58% | 47% |
| Worst month | -7.2% | -7.6% | -5.9% |
| 2022 / 23 / 24 / 25 / 26 | +2.1 / +62.8 / +57.7 / +10.6 / +19.0% | | -8.9 / +58.7 / +49.1 / +11.6 / +20.3% |

**Prop:** $100k, 2 years, bootstrap of 500 paths.

| Firm | Book | Setting | Pass | Days | Mean net | Unlucky 10% | P(profit) |
|---|---|---|---|---|---|---|---|
| FTMO 2-Step | swap-free | 1.5 / 1.0 / 60% | 69% | 100 | **$34.7k** | **$12.0k** | 98.2% |
| FundedNext Stellar | swap-free | 1.5 / 1.0 / 60% | 72% | 90 | **$35.9k** | **$12.9k** | 98.6% |
| BrightFunded Classic | swap-free | 1.5 / 1.0 / 60% | 69% | 101 | **$34.6k** | **$12.0k** | 98.0% |
| FTMO 2-Step | swap-free | 1.0 / 0.6 / 50% | 86% | 174 | $18.8k | $4.9k | 96.2% |
| FTMO 2-Step | base | 1.5 / 1.0 / 60% | 66% | 106 | $25.7k | $3.0k | 93.4% |
| FundedNext Stellar | base | 1.5 / 1.0 / 60% | 63% | 103 | $26.7k | $3.3k | 94.2% |

**Pass rate vs payout:** a higher challenge risk lowers the pass rate per attempt (about 70% vs 86%), but it passes faster and is paid more once funded. With up to 5 attempts in the simulation, the net result is clearly higher.

## Verdict
- **The swap matters most for CFD firms.** On a swap-free crypto account, the CFD book becomes almost as good as the crypto-firm book:
  - swap-free CFD: Sharpe 1.81, about $35k per $100k over 2 years;
  - crypto-firm v5: Sharpe 2.25, about $42k at HyroTrader with the Gen79 settings.
- **Action for the user:** ask each CFD firm (FTMO, FundedNext, BrightFunded, ...) whether a swap-free account is available, and whether crypto CFDs on it are swap-free or carry an admin fee instead.
  - **If swap-free:** use the 4-sleeve book.
  - **If not:** use C* + Weiss.

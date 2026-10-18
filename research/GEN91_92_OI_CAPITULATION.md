# Gen91-92: open-interest family and capitulation signals (2026-10-18)

- **Protocols:** `config/gen91_protocol.json` (4 trials) and `config/gen92_protocol.json` (4 trials), both registered before any number.
- **Scripts:** `scripts/gen91_oi.py`, `scripts/gen92_capit.py`, `scripts/gen90_v6_prop.py`.
- **Baseline:** the Gen90 CFD book (swap-aware C\* + Weiss + deleveraging bounce), Sharpe 1.797.
- **The Gen89 bounce rule was not re-tuned.**

## Gen91: the open-interest family

| Test | DEV 2022 | TEST 23-24 | HOLD 25-26 | Book after | Verdict |
|---|---|---|---|---|---|
| K1 bounce on the 9 CFD altcoins | -0.20 | 0.95 | 0.39 | 1.48 | rejected as a sleeve (10 bp spreads; corr 0.66 with the BTC/ETH bounce) |
| K2 short-covering fade (OI down, price up -> short) | 0.24 | -0.79 | 0.38 | 1.80 | rejected (6 signals) |
| K3 leverage build-up fade (OI up, price up -> short) | -0.89 | -0.63 | 0.73 | 1.40 | rejected |
| K4 bounce on 20 coins, perp, inside v5 | -0.03 | 1.14 | 0.76 | v6 2.48 vs 2.46 | not adopted: must beat the BTC/ETH bounce on DEV too |

**K1 per coin, 2022-26:**
- Positive on 7 of 9: SOL 0.63, ADA 0.46, DOT 0.40, XRP 0.37, AVAX 0.33, LTC 0.28, DOGE 0.06.
- Negative on 2: LINK -0.18, BCH -0.07.

This is cross-sectional out-of-sample support for the BTC/ETH bounce: the effect is broad, not a quirk of two coins.

## Gen92: capitulation signals

| Test | DEV | TEST | HOLD | Book after | Verdict |
|---|---|---|---|---|---|
| L1 DVOL jump > 10% on a down day -> long 2 days | 0.12 | -0.35 | -0.49 | 1.67 | rejected |
| L2 volume > 3x average on a down day -> long 2 days | 0.42 | 0.40 | 0.78 | 1.80 (too few signals for a weight) | rejected (21 signals, TEST < 0.5) |
| L3 VIX / VIX3M > 1 -> long US500 + US100 for 3 days | 0.15 | 0.74 | 0.36 | 1.64 | rejected: passes alone, lowers the book |
| L3 variant ratio > 1.05 | 0.14 | no trades | 0.52 | 1.72 | variant |

**L3 pre-check, 2007-17 (Yahoo daily):** Sharpe 0.20. It is a real but weak equity effect, and it adds equity crash risk that the crypto book does not need.

## Candidate v6 for the crypto firms (v5 + deleveraging bounce, Gen90 test passed)

| | Sharpe 2022-26 | CAGR | Max DD | Positive months | 2022 / 23 / 24 / 25 / 26 |
|---|---|---|---|---|---|
| **v6** | **2.46** | 43.0% | -9.4% | 72% | +29 / +59 / +68 / +14 / +39% |
| v5 | 2.28 | 39.1% | -9.5% | 72% | +19 / +64 / +65 / +11 / +35% |

| HyroTrader ($100k, 2 years, bootstrap) | Setting | v6 mean / unlucky 10% / P(profit) | v5 mean / unlucky 10% / P(profit) |
|---|---|---|---|
| 1-Step | 1.25 / 1.0 / 60% | **$46.0k / $18.8k / 99.4%** | $41.9k / $14.0k / 98.0% |
| 2-Step | 1.5 / 1.0 / 50% | **$46.4k / $21.5k / 99.8%** | $42.4k / $18.1k / 99.2% |

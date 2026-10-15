# Gen62: market-neutral and bear-phase crypto sleeves (2026-10-15)

**Protocol:** `config/gen62_protocol.json`, registered before running. **Script:** `scripts/gen62_crypto.py`. **Results:** `results/gen62_crypto.csv`.

**Periods:** DEV 2020–22 (includes the 2022 bear market) | TEST 2023–24 | HOLD 2025–26.

**Pass rule:** TEST >= 0.8, HOLD >= 0.5, DEV > 0, correlation with C* <= 0.3. A variant counts only if its neighbouring settings are also stable.

| Idea | Best result | Verdict |
|---|---|---|
| H1 pairs trading (cointegration, 190 pairs, monthly re-selection; 6 settings) | primary 2023+ -1.00; the best variant only -0.03 | **rejected**: crypto pairs drift apart instead of reverting |
| H2a residual premium (7d minus 60d) | TEST -1.48 | rejected |
| H2b premium + funding rank | 2023+ 0.71 (below G4's 1.01) | rejected |
| H2c G4 with inverse-vol legs | 2023+ 1.02 (G4: 1.01) | not better by >= 0.10 → **G4 stays** |
| H3 bear short sleeve (only when BTC < 200d MA; 4 settings) | **2022: +13% to +16%**, but DEV -0.6 and 2023+ -0.35 to -0.45 | **rejected**: it earns in a real bear year but loses in every other dip |
| H4 cascade with BTC > 200d filter (4 settings) | TEST 1.38–1.70, but HOLD 0.08–0.28, DEV < 0 | rejected: the filter **lowers** HOLD (unfiltered: 0.91) |

**Bug found and fixed in H4:** when more than 3 coins cascaded in the same hour, the first version broke the tie by outcome (worst trade first). Ties are now broken by coin name. The earlier cascade results (Gen57, `crypto_sleeves.py`) did not have this bug.

## Portfolio weights (H7, descriptive)

3 sleeves (C*, premium carry, cascade), 2022–26, at 15% vol:

| Weighting | Sharpe | 2023+ | Positive months | Max DD | 2022 |
|---|---|---|---|---|---|
| Equal risk | **1.56** | 1.98 | **61%** | -17% | -5% |
| Inverse-vol monthly | 1.53 | 1.83 | 56% | -19% | -2% |

Equal risk stays.

## Crypto-firm sizing for the 3-sleeve portfolio

Hourly path 2022–26, $100k account, up to 5 challenges, 24 months. This is descriptive and selected on the same data.

| Firm | Best setting found | Pass | Net 2 years (average / unlucky 10%) | Months with income |
|---|---|---|---|---|
| HyroTrader 1-Step | 1.0x / 0.6x | 74% | $19.8k / $14.3k | 35% |
| HyroTrader 2-Step | 1.25x / 0.5x | 78% | $19.2k / $13.0k | 36% |
| SizeProp 1-Step | 1.0x / 0.6x | 54% | $18.8k / $14.7k | 38% |
| CFT 1-Phase | 1.0x / 0.6x | 59% | $15.7k / $10.5k | 29% |
| Breakout Classic | 1.0x / 0.4x | 59% | $10.1k / $6.0k | 27% |

Higher risk (1.5x) raises daily-loss failures sharply at the 3%-daily firms (SizeProp, Breakout).

## Conclusion

Within crypto, **C* + premium carry + cascade at equal risk** is the best mix found: about 1.55 Sharpe over 2022–26 and about 2.0 over 2023+. None of the four new market-neutral or bear ideas passed.

The remaining weakness is a crypto bear year (2022: -5%). The only sleeve that earned in 2022 (H3) loses the rest of the time.

# Gen84: new crypto ideas for a higher Sharpe, and swap-free firm facts (2026-10-18)

Protocol: `config/gen84_protocol.json`, registered before any number was computed. 5 trials. Script: `scripts/gen84_sharpe.py`.
The baseline is v5, with a 2022-26 Sharpe of 2.275 after the C* 2-day lag fix.

## Results (yearly-scaled daily Sharpe; perp costs 5 bp plus funding)

| Test | DEV 20-22 | TEST 23-24 | HOLD 25-26 | Corr C* | v5 + it (2022-26) | Verdict |
|---|---|---|---|---|---|---|
| M1 MAX effect, 7-day (PRIMARY) | -0.82 | -0.63 | -0.44 | -0.22 | 2.13 | rejected |
| M2 MAX effect, 30-day (variant) | -1.20 | -0.83 | 1.53 | -0.23 | 2.31 | variant only; fails DEV and TEST |
| I1 idiosyncratic vol vs BTC (PRIMARY) | -0.92 | -0.99 | 0.64 | -0.20 | 2.27 | rejected |
| T1 turn-of-month BTC/ETH (PRIMARY) | 1.18 | -1.15 | 0.01 | 0.22 | 1.86 | rejected |
| V1 DVOL VRP overlay on v5 (PRIMARY) | - | 3.33 (v5 3.35) | 1.61 (v5 1.68) | - | 2.26 | rejected; max DD -11.6% vs -10.7% |

Findings:
- The equity "lottery" (MAX) and IVOL anomalies do not hold in the 20-coin perp universe at weekly horizons.
- Turn-of-month only worked in 2020-22.
- VRP timing adds nothing over v5's own vol targeting.
- M2's HOLD 1.53 is a single-period result and was not promoted, per the protocol.

**v5 and the swap-free CFD book are unchanged.**

## Swap-free crypto CFD accounts (web research, 2026-10-18; confirm with the firm before buying)

- **FundedNext:** swap-free is available on all challenge types as an add-on at about +10% of the fee, with the same spreads, crypto included. This is per its help centre (help.fundednext.com, article "Does FundedNext offer swap-free accounts").
  - Simulator preset added: `FundedNext Stellar 2-Step $100k swap-free`, fee $604.99, swap 0.
  - Swap-free book at 1.5 / 1.0 / 60%: P(pass) 72%, about $35.9k mean net over 2 years, p10 $12.9k, P(profit) 98.6%. The fee add-on costs about $50 of mean.
- **FTMO:** sources conflict.
  - fundedtrading.com lists swap-free on request.
  - propvator.com and thegodfunded.com say it is not offered.
  - Treat it as **not available** unless FTMO support confirms it in writing.
- **BrightFunded:** sources conflict (an add-on vs not offered).
  - It lists 35-40 crypto pairs, 5:1 crypto leverage and about 0.024% commission (benzinga.com review, propvator.com).
  - Confirm with support.

**Practical choice for the swap-free book: FundedNext Stellar 2-Step with the swap-free add-on.**

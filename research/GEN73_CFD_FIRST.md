# Gen73: first CFD-firm tests on Dukascopy hourly data

- **Protocol:** `config/gen73_protocol.json`, registered before any result.
- **Script:** `scripts/gen73_cfd.py`.
- **Results:** `results/gen73_cfd.csv`.
- **Data:** US100, US500, US30, DE40, XAUUSD, EURUSD hourly, 2013-01..2026-09.
- **Costs:** 1 bp per side for indices and EURUSD, 2 bp for gold, plus 3%/yr financing for positions held overnight.
- **Trials added:** 9.

| Test | DEV 13-19 | TEST 20-23 | HOLD 24-26 | Fresh 23-10..26-09 | All | Corr v5 | Verdict |
|---|---|---|---|---|---|---|---|
| T1 gold session split (Gen60 D2) | -0.32 | -0.80 | -0.40 | -0.40 | -0.47 | 0.00 | rejected |
| T1 variant: long leg only | -0.32 | -0.36 | 0.52 | 0.59 | -0.05 | 0.03 | info |
| T2 European-open long, US500 (Gen48c re-test) | -0.50 | 0.34 | -0.68 | **-0.71** | -0.07 | 0.01 | rejected |
| T2 European-open long, DE40 | 0.27 | 0.37 | 0.40 | 0.41 | 0.34 | 0.03 | below 0.5 |
| T3 overnight, US500 (Liu & Tse re-test) | 0.07 | 0.00 | 0.52 | 0.67 | 0.12 | 0.05 | see note |
| T3 overnight, US100 | 0.55 | 0.24 | 0.81 | 0.90 | 0.46 | 0.04 | see note |
| T3 overnight, US30 | -0.09 | -0.07 | -0.71 | -0.48 | -0.19 | 0.05 | rejected |
| T4 noise-area breakout, US100, hourly checks (Gen47 re-test) | 0.60 | 0.34 | -0.37 | **-0.59** | 0.33 | 0.02 | rejected |
| T5 4h breakout trend, 6 CFDs (crypto rule) | -0.27 | -0.45 | -0.67 | -0.26 | -0.41 | 0.14 | rejected |
| T5 variant: indices + gold | -0.06 | -0.34 | -0.53 | -0.08 | -0.24 | 0.15 | info |

## Reading
- **Gold session split.** It worked in the paper's own era: 2013-02..2015-02 gives +0.76, the period that was registered to be reported separately. Since 2015 it is -0.72. This is the familiar decay of a published calendar anomaly.
- **Overnight index returns.** On US100 the fresh period gives 0.90 and on US500 0.67. This is not counted as a pass. The Gen59 rule needs the same sign as the original result, and the original was negative after costs. The overnight hold is also mostly long equity beta in a strong 2023-26 market: US30 is negative over the same period, and 2020-23 is about zero.
- **Noise-area breakout.** The fresh period is negative (-0.59), so the Gen47 candidate fails its out-of-sample re-test. Checking only every hour is a weaker version of the 30-minute rule, but the sign flip is decisive.
- **4h breakout trend.** The crypto trend rule does not transfer to index, gold and FX CFDs. It is negative on 5 of the 6, and only gold is slightly positive. This matches Gen40 (multi-asset CFD trend rejected).

## What this means for CFD firms
None of the classic index and gold timing effects survives realistic CFD costs on fresh data. The most realistic CFD-firm route is still **crypto at CFD firms**: FTMO-type firms offer BTC/ETH (and some alt) CFDs, where C* already ran in Gen52 (FTMO 2-Step, about $12k net over 2 years on the hourly replay). Next, once the BTCUSD / ETHUSD and FX hourly files arrive:
- **C* + 4h trend + Weiss on BTC/ETH CFDs** with real CFD prices, spreads and swaps (Gen59 item);
- **the FX fix pattern (Gen60 D1)** on 7 USD pairs, plus the month-end overlay (D4);
- **the multi-asset trend re-test (Gen40)** on all 35 CFDs.

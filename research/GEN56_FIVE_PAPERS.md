# Gen56: five crypto papers (2026-10-14)

Protocol: `config/gen56_protocol.json`, registered before testing. Script: `scripts/gen56_papers.py`. Results: `results/gen56_*.csv`.

The tests use the data already in the repo:

- OKX USDT perps, hourly, 58 coins, 2020–2026;
- Binance spot, daily (2017+) and hourly (2022+);
- Binance BTC/ETH funding, 2020–2023.

The user's Binance futures pack will allow cleaner re-tests; those are pre-registered in `config/gen57_protocol.json`.

## A. Intraday hour pairs: Wen, Bouri, Xu & Zhao (2022)

**What the paper claims.** Certain UTC hours predict later hours on BTC, some as momentum and some as reversal. The paper's sample ends in 2020-05, so everything from 2020-06 onwards is a true out-of-sample test.

**What we tested:**

- the 7 published pairs, plus a combination of the 5 pairs the paper calls effective;
- 7 markets: OKX perps BTC, ETH, LTC, XRP and Binance spot BTC, ETH, XRP;
- 3 variants: as published, skip jump hours, trade only low-liquidity hours;
- costs of 0, 2 and 5 bp per side.

**Results:**

- **Before costs:** combined Sharpe −0.8 to +1.1 in 2020-06..2022 and −0.6 to +0.3 in 2023+. Single pairs flip sign between periods.
- **After costs:** with one round trip per day, even 2 bp per side gives Sharpe −1 to −3.
- **Exploratory search over all 276 BTC hour pairs:** only 1 pair reached |t| ≥ 3 on 2020–22 (r19→r20), and it lost money in 2023+ (Sharpe −1.3).

**Verdict: rejected.** The published pattern did not persist after the paper's sample.

## B. Basis, momentum and basis-momentum factors: Chi, Hao, Hu & Ran (2023); Cao et al. (2026)

**What the paper claims.** Long the coins with the highest basis (spot above futures), short the lowest, hold 1 day: +329% a year on OKX quarterly futures in 2017–21.

**What we tested:**

- basis = Binance spot close vs OKX perp close at the same instant (00:00 UTC);
- the 10 majors, long top third / short bottom third;
- 48 configurations: basis, momentum and basis-momentum × lookbacks J 1/3/5/7 × hold 1/7 days × entry lag 0/1 hour;
- costs of 5 bp per side.

**Results:**

- **Basis, the paper's main factor (J=5, hold 1 day):**
  - after costs: DEV 2020–22 Sharpe +0.23 (lag 0) / −0.30 (lag 1h); TEST 2023+ −0.48 / −0.42;
  - before costs: TEST Sharpe +0.71, but turnover is 2.5× the portfolio per day, so costs remove all of it.
- **The basis we measured is cross-exchange,** with a median of only about 3 bp, so it is noisy. A clean re-test uses Binance's premium index (`get_binance_premium.bat`).
- **Momentum and basis-momentum:** no configuration is positive in both periods except basis-momentum J=5, hold 7 (DEV +0.17, TEST +0.81). One survivor out of 48 is what chance alone would produce. Not passed.
- **Cross-sectional momentum on all 58 OKX perps:**
  - DEV 2020–22 Sharpe +0.3 to +1.1 for 5–30 day lookbacks; TEST 2023+ −0.1 to −1.2;
  - the reversal versions are negative in both periods;
  - the universe holds only coins still listed today, which flatters the backtest.
- **Cao et al. price-volume factor:** only the abstract is available, and it does not define the factor. Not tested.

**Verdict: rejected on this data.** The paper's very large returns come from 2017–21 quarterly futures and do not carry over to perps in 2020–26 once costs are included. The basis factor gets one more chance on clean premium-index data (Gen57, T6).

## C. Funding-rate predictability: Inan (2025)

**Forecasting replicates.** An AR(1) forecast (the mean equation of the paper's DAR model) on a rolling window of 500 prints beats "no change":

| | MSPE vs no change | Direction correct |
|---|---|---|
| BTC 2020–23 | 7% lower | 61% of the time |
| ETH 2020–23 | 9% lower | 62% of the time |

**Trading does not.** A contrarian trade on the forecast (short when predicted funding is above 0.03% per 8h, long when it is negative) gives Sharpe +0.11 on BTC and −1.0 on ETH. Rejected.

**Useful by-product: funding cost of C\*.** If C\* + BTC leads holds BTC and ETH as perpetuals, funding costs about 0.8% of equity per year per coin (2020–23). Across all 10 coins it would plausibly total about 2–4% a year, a real cost at perp-based prop firms (HyroTrader, SizeProp, CFT). Gen57 T9 measures it on all coins.

## D. Arbitrage in perpetual contracts: Dai, Li & Yang (2025)

The paper derives theoretical no-arbitrage bounds for perpetual futures prices. Trading on them needs a spot position and a perp position at the same time, which a prop account cannot hold. Its testable implication, that a premium outside the bounds reverts, is pre-registered as Gen57 T6 on premium-index data.

## Trials

About 330 configurations, counted toward the project total.

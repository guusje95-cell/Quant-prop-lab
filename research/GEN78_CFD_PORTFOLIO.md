# Gen78: low-turnover CFD ideas on 35 instruments, and the CFD-firm portfolio

- **Protocol:** `config/gen78_protocol.json`.
- **Scripts:** `scripts/gen78_cfd.py` (tests) and `scripts/gen78_cfd_report.py` (portfolio report).
- **Chart:** `results/gen78_cfd_portfolio.png`.
- **Trials added:** 6.

## Tests (DEV 2013-19 / TEST 2020-23 / HOLD 2024-26, CFD costs + 3%/yr financing)
| Idea | DEV | TEST | HOLD | All | Verdict |
|---|---|---|---|---|---|
| M1 XS momentum 12-1 within FX / indices / commodities (Asness, Moskowitz & Pedersen) | -1.25 | -0.19 | -0.14 | -0.71 | rejected |
| M1 variant 6-1 | -0.92 | -0.15 | -0.16 | -0.55 | rejected |
| M2 pairs mean reversion (WTI/Brent, gold/silver, AUD/NZD, EU50/DE40, FR40/EU50, US500/US30) | -0.90 | -0.16 | -0.74 | -0.51 | rejected |
| M2 variant entry 1.5 sigma | -1.29 | -0.39 | -0.96 | -0.83 | rejected |
| M3 FX intraday seasonality (Breedon & Ranaldo) | -0.18 | -0.86 | -1.18 | -0.54 | rejected |
| M3 variant + US-hours leg | -0.38 | -0.96 | -1.78 | -0.79 | rejected |

**By class:** momentum is negative in FX (-0.81) and indices (-0.44) and flat in commodities (+0.01, with HOLD +0.60).

**Two scripting errors, fixed before the results were used:**
- An early zero-volatility division gave NaN / infinite weights in the first months.
- The fix makes the strategy flat until 1 year of history exists.

## Non-crypto CFD research: final tally (Gen73-78)
- **31 ideas tested:** index timing, gold, FX fix, FX seasonality, breakouts, trend, XS momentum, pairs, month-end, vol management. None passes.
- **Near misses:** RSI(2) pullback, pre-FOMC drift, US100 noise-area. These are cost-limited index ideas that belong to the futures test (Databento).

## The CFD-firm portfolio = crypto CFD book (C* + Weiss expiry as CFDs)
- **Setup:** C* includes the 2-day stablecoin lag found in paper trading. Point-in-time equal risk, Weiss at half weight.
- **Costs:** 5 bp per side for BTC/ETH CFDs, 10 bp for others. Swap on overnight notional; no funding.

| | Base (swap 3.3 bp/day) | Swap 6.6 bp/day | 2x spread | Crypto-firm v5 (reference) |
|---|---|---|---|---|
| Sharpe 2022-26 | **1.57** | 1.47 | 1.24 | 2.25 |
| Sortino | 2.86 | 2.66 | 2.19 | 4.33 |
| CAGR at 15% vol | 25.1% | 23.3% | 19.0% | 38.7% |
| Max drawdown | -16.0% | -16.4% | -17.4% | -9.5% |
| Longest drawdown | 393 days | 393 | 400 | 172 |
| Positive months | 47% | 47% | 46% | 72% |
| Worst month / day | -5.9% / -6.5% | | | -4.2% / -3.6% |
| 2022 / 2023 / 2024 / 2025 / 2026 (Jan-Sep) | -8.9 / +58.7 / +49.1 / +11.6 / +20.3% | | | +18.8 / +63.3 / +64.0 / +10.6 / +34.2% |

**Prop at base costs** ($100k, 2 years, bootstrap, daily stop at 50% of the firm's limit):

| Firm | Risk | Pass | Days | Mean net | Unlucky 10% | P(profit) |
|---|---|---|---|---|---|---|
| FTMO 2-Step | 1.0 / 0.6 | 84% | 172 | $15.0k | $0.3k | 91% |
| FundedNext Stellar 2-Step | 1.0 / 0.6 | 90% | 173 | $15.8k | $1.1k | 92% |
| BrightFunded 2-Step Classic | 1.0 / 0.6 | 84% | 172 | $15.0k | $0.2k | 91% |

At a swap of 6.6 bp/day the mean net is $14.0-14.8k and P(profit) is 88-91%.

## Verdict
- **CFD firms work as a second channel:** about $15k per $100k account over 2 years at FTMO-type firms.
- **Crypto firms stay first:** about $26k per account, with a much steadier path.
- **Weaknesses of the CFD book:**
  - only two strategies, both crypto;
  - half the months negative;
  - a losing 2022;
  - challenges take about 6 months.
- **Before buying at a CFD firm:** check its crypto CFD swap rate. Above 24%/yr the edge thins quickly.
- **Diversifying CFD accounts beyond crypto** is not possible on CFD costs with anything tested so far. The futures route (Databento) is where index edges might survive.

# Gen77: full Dukascopy set - FX fix, month-end overlay, 5-minute noise-area re-test, crypto CFD check

- **Protocol:** `config/gen77_protocol.json`, registered before any result.
- **Script:** `scripts/gen77_dukascopy.py`.
- **Results:** `results/gen77.csv`.
- **Trials added:** 6.

| Test | DEV 13-19 | TEST 20-23 | HOLD 24-26 | Fresh 23-10..26-10 | All | Verdict |
|---|---|---|---|---|---|---|
| X1 FX fix pattern, London + Tokyo, 7 USD pairs (Krohn et al.) | -4.07 | -3.22 | -5.81 | -5.97 | -4.07 | rejected |
| X1 variant: London only | -2.65 | -2.29 | -3.84 | | -2.72 | rejected |
| X2 month-end equity rebalancing overlay (FX) | -0.62 | -0.38 | -0.77 | -0.34 | -0.46 | rejected |
| X3 noise-area breakout, 5-minute data, US100 (Gen47 re-test) | 1.04 | 0.78 | 0.45 | **0.44** | 0.75 | fails (fresh < 0.5; near miss) |
| X3 same, US500 | 0.77 | 0.77 | -1.18 | **-1.15** | 0.23 | rejected |

**X1 diagnosis.**
- **The pattern exists before costs, but it is tiny.** The USD weakens after the Tokyo fix by +0.76 bp/day (2013-19) and +0.49 bp/day (2020-26), and after the London fix by +0.33 / -0.32 bp/day. The before-fix leg is about 0.
- **Costs dominate.** A round trip with a flip costs about 4 bp per fix. A pattern measured in fractions of a basis point cannot be traded through CFD spreads.

**X3 diagnosis.**
- **This is the exact paper rule:** 30-minute checks, VWAP stop, 2% daily vol target.
- **US100 stays positive:** 0.75 over 2018-26, but only 0.44 on the fresh period.
- **US500 turns clearly negative after 2024.**
- **The hourly-bar failure in Gen73 was partly a resolution problem.** Even so, the fresh period does not confirm the edge on CFD costs. It remains a futures-firm candidate at lower cost; Databento NQ/ES is the right test.

## X4: crypto CFD data check (Dukascopy BTCUSD / ETHUSD vs Binance)
| Rule | Daily correlation, Dukascopy vs Binance | Sharpe 2018-22 (Duka / Binance) | Sharpe 2023-26 (Duka / Binance) |
|---|---|---|---|
| trend 4h, BTC + ETH, close-based channel, 5 bp + 3.3 bp/day swap | 0.94 | 0.87 / 0.28 | 0.40 / 0.69 |
| Weiss expiry, BTC + ETH | 0.96 | 0.55 / 0.36 | 1.42 / 1.14 |

Real CFD prices behave like the Binance prices (correlation 0.94-0.96, same signs). **The Gen74 crypto-CFD result is confirmed:** C* + Weiss as CFDs at FTMO-type firms.

## CFD-firm bottom line after Gen73-77
- **Non-crypto CFD ideas tested so far:** 25 (index timing, gold, FX fix, FX breakout, month-end, trend). None passes on CFD costs.
- **CFD firms should run the crypto CFD book** (C* + Weiss, Sharpe about 1.5).
- **Index intraday edges** (noise-area, RSI(2), pre-FOMC) are near misses that may work at futures cost. That is the next test, with Databento.

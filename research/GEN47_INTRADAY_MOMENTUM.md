# Gen47: two intraday momentum papers on US index CFDs (pre-registered)

The protocol was written before any run: `config/gen47_intraday_momentum_protocol.json`.
- **Code:** `src/qpl/lab/strategies_papers.py` and `scripts/gen47_intraday_momentum.py`.
- **Results:** `results/gen47_intraday_momentum.csv`.
- **Settings:** paper defaults throughout; nothing was tuned.
- **Data:** Dukascopy US500 and US100 CFDs, converted to New York time. 15-minute bars cover 2013-08 to 2023-09. 5-minute bars cover 2020-09 to 2023-09.

| Strategy | Asset | Cost (bp/side) | Net Sharpe | CAGR | Max DD | Sharpe <2018-09 | Sharpe ≥2018-09 |
|---|---|---|---|---|---|---|---|
| Gao et al. 2018: first half hour → last half hour | US500 15m | 1.0 | **−1.06** | −5.2% | −44% | −1.61 | −0.88 |
| | US100 15m | 1.0 | −0.85 | −4.7% | −40% | −1.11 | −0.80 |
| | US500 15m | 0.3 | −0.37 | | | | |
| Zarattini et al. 2024: noise-area breakout | US500 15m | 1.0 | **0.36** | 3.1% | −25% | −0.24 | 0.86 |
| | US100 15m | 1.0 | 0.71 | 7.2% | −17% | 0.62 | 0.79 |
| | US500 15m | 0.3 | 0.88 | 8.2% | −16% | 0.38 | 1.28 |
| | US100 15m | 0.3 | 1.12 | 12.0% | −12% | 1.09 | 1.15 |
| | US500 5m (2020–23) | 1.0 | 1.11 | 12.2% | −9% | | |
| | US100 5m (2020–23) | 1.0 | 1.05 | 11.7% | −7% | | |

## Verdict under the pre-registered rule

**The rule:** Sharpe ≥ 0.8 on US500 15-min at 1 bp, positive in both halves, and positive on US100.

- **Gao: REJECTED.** It is negative everywhere, even before most of the cost. This matches later studies, which found that the effect faded after the paper's 1993–2013 sample.
- **Noise-area breakout: NOT PASSED on the primary test.**
  - US500 at 1 bp gives Sharpe 0.36, and its first half is negative.
  - It is positive in 9 of the 10 noise-area runs above. The exception is US500 at 2 bp.
  - It holds up on US100 in both halves and on the 2020–23 5-minute data.
  - The result is very sensitive to cost. At real-futures cost (0.3 bp) it is Sharpe 0.9–1.1. At 2 bp it is about zero.
  - Deflated Sharpe, counting the 16 trials of this generation, is 0.26 for the primary test and 0.97 for the best run. The best run is not the pre-registered primary.

## What this means

The noise-area breakout is the first intraday result in this project with a consistent positive sign. It only works where costs are very low: real CME futures (ES, NQ or the micros) or a very tight CFD spread.

It is a candidate for a futures prop firm, not a CFD one. It is not validated, because it failed the pre-registered primary test.

Next steps if it is pursued:
1. Get real ES/NQ 5-minute data back to 2010 and re-test once, with costs of 0.3–0.6 bp.
2. Check the 2% daily-volatility target against the prop firm's daily loss limit in the Lab's prop tab.

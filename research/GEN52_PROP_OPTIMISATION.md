# Gen52: optimising strategies and prop settings (pre-registered)

- **Protocol:** `config/gen52_optimization_protocol.json`, written before running.
- **Scripts:** `scripts/gen52_optimize.py`, `scripts/gen52_extra_check.py`.
- **All results:**
  - `results/gen52_stage1.csv`: 108 strategy/sizing variants.
  - `results/gen52_stage2.csv`: 5,760 prop-setting runs.
  - `results/gen52_final.csv`: top 10 per firm on TEST and HOURLY.
- **Total trials in this generation:** about 5,900.

## Method

- **Choosing vs. judging:** all choices were made on **DEV 2018–2022**. The finalists were judged once on **TEST 2023–2026** and on a **HOURLY** replay (2022–2026, real hourly price paths; stops and take-profits fill where they actually trigger).
- **Goal:** average 24-month net cash, buying up to 5 challenges. Primary firm Crypto Fund Trader 1-Phase $100k; FTMO 2-Step $100k ranked separately.
- **Stage 1: strategy and sizing variants.** Each backtest was rescaled to 15% volatility using DEV volatility only.
  - **18 signal variants:**
    - C* with/without the stablecoin filter, long-only or long-short;
    - 3 Catching Crypto Trends ensembles;
    - Donchian 10/20/55;
    - time-series momentum 30/60/90;
    - moving-average crossover 20/100 and 50/200;
    - N-day high breakout 20/50;
    - C* + CCT blend.
  - × volatility lookback 20/30/60 days × no-trade band 0/0.2.
- **Stage 2: prop settings for the top 8 variants per firm:**
  - challenge risk 0.5–1.5×;
  - funded risk 0.25/0.4/0.6×;
  - daily equity stop at 0/50/75/90% of the firm's daily limit;
  - daily take-profit off/2%/4%;
  - cushion scaling on/off.

## Stage 1: which strategy variants were best on DEV (CFT 1-Phase, default prop settings)

| Variant | DEV Sharpe | CFT pass | CFT net (24 mo) |
|---|---|---|---|
| C* default, vol 20, band 0.2 | 1.89 | 42% | $21,706 |
| C* + CCT 50/50, vol 20, band 0.2 | 1.81 | 41% | $21,177 |
| C* + CCT 50/50, vol 30 | 1.80 | 43% | $21,005 |
| C* no stablecoin filter, vol 20, band 0.2 | 1.76 | 35% | $20,899 |
| CCT 5..360, vol 60 | 1.70 | 55% | $20,717 |
| C* default, vol 30 (plain C*) | 1.83 | 29% | $20,715 |

Donchian, momentum, moving-average and N-day variants ranked lower (all in the CSV). Long-short C* was worse than long-only.

## Stage 2: what each prop setting does on average (DEV, all 2,880 runs per firm)

| Setting | CFT 1-Phase avg net | FTMO avg net | Effect on pass rate |
|---|---|---|---|
| Challenge risk 0.5 / 0.75 / 1.0 / 1.25 / 1.5 | 12.5k / 13.9k / **13.9k** / 13.6k / 13.1k | 15.7k / 17.7k / **18.8k** / **18.8k** / 18.0k | Lower risk = more passes, but slower and smaller |
| Funded risk 0.25 / 0.4 / 0.6 | 10.6k / **15.9k** / 13.8k | 11.7k / 18.0k / **23.7k** | — (FTMO's 10% static max loss allows more risk) |
| Daily stop 0 / 50% / 75% / 90% | 12.0k / 11.1k / 14.5k / **16.0k** | 16.7k / 16.0k / 18.9k / **19.6k** | +7–24 points with a 75–90% stop |
| Take-profit 0 / 2% / 4% | 13.2k / 13.5k / 13.5k | 17.6k / 17.8k / 18.0k | Almost no effect |
| Cushion scaling off / on | **14.8k** / 12.0k | **18.9k** / 16.7k | More passes, but less money |

## Final: top DEV configurations on TEST 2023–2026 and HOURLY, against plain C*

**Crypto Fund Trader 1-Phase** (plain C* = vol 30, risk 1.0 / 0.4, no stop or take-profit)

| Config | TEST net | TEST P(profit) | HOURLY pass | HOURLY net | HOURLY P(profit) |
|---|---|---|---|---|---|
| **Plain C\*** | $2,208 | 78% | 31% | **$10,157** | 98% |
| Best DEV: C* no filter, vol 20, band 0.2, 1.25 / 0.6, stop 90%, TP 2% | $16,632 | 92% | 24% | $6,342 | 97% |
| C* default, vol 20, band 0.2, 1.0 / 0.6, stop 90%, TP 4% | $11,029 | 94% | 38% | $7,499 | 97% |
| C* default, vol 20, band 0.2, 0.75 / 0.6, stop 90%, TP 4% | $10,277 | 88% | 45% | $5,286 | 97% |
| C* + CCT, vol 30, band 0.2, 1.5 / 0.6, stop 90%, TP 2% | $18,795 | 90% | 22% | $7,711 | 91% |
| C* default, vol 20, band 0.2, 1.0 / 0.4 (sizing tweak only) | $3,689 | 89% | 38% | $9,573 | 98% |

**Verdict for CFT 1-Phase: no optimised configuration is proven better.** All 10 beat plain C* on the daily-candle TEST, but on the realistic hourly replay every one earns less (or about the same).

**Why:**
- The daily-candle model assumes all coins hit their lows together. That makes stops trigger far more often than they really do, and fills take-profits at exactly the target.
- On real hourly paths the stop and take-profit rarely matter.
- Higher risk or funded size mostly adds variance.

**FTMO 2-Step** (plain C* = vol 30, risk 1.0 / 0.4)

| Config | TEST pass | TEST net | TEST P(profit) | HOURLY pass | HOURLY net | HOURLY P(profit) |
|---|---|---|---|---|---|---|
| **Plain C\*** | 49% | $6,874 | 95% | 63% | $10,921 | 97% |
| **C\* no stablecoin filter, vol 20, band 0.2, challenge 1.5×, funded 0.6×, daily stop 90%, TP 4%** | **65%** | **$15,539** | **97%** | 54% | **$12,277** | **99%** |
| C* default, vol 20, band 0.2, 1.5 / 0.6, stop 90%, TP 2% | 69% | $20,078 | 97% | 46% | $10,494 | 99.5% |
| C* + CCT, vol 30, 1.5 / 0.6, stop 90%, TP 2% | 68% | $20,891 | 97% | 43% | $8,946 | 97% |
| C* no filter, vol 20, band 0.2, 1.25 / 0.6, TP 4% | 63% | $9,614 | 93% | 49% | $14,431 | 97% |

**Verdict for FTMO: one configuration meets the pre-registered rule.** It beats plain C* on TEST net and chance of profit, and the hourly replay confirms both (+$1,356, 99% vs 97%).

**Caveats:**
- It was one of 10 finalists checked against the rule, out of about 5,900 trials.
- Its hourly pass rate per attempt is lower (54% vs 63%). The extra money comes from trading the funded account at 0.6× instead of 0.4×, which FTMO's 10% static max loss allows.
- Treat it as **promising, to be paper traded**, not as proven.

## What to take away

1. **CFT 1-Phase:** keep plain C*: challenge 1.0×, funded 0.4×. None of the extras (stop, take-profit, cushion, more risk) holds up on real hourly prices.
2. **FTMO 2-Step:** the optimised setup above. The parts that matter: more risk in the challenge (1.5×) and when funded (0.6×), since FTMO allows a 10% drawdown. The 90% daily stop protects against the 5% daily limit.
3. **Strategy choice:** C* stays best. The 20-day volatility window and the 0.2 no-trade band are small, consistent improvements on DEV, but not proven on hourly data. Both are now settings in the app.
4. **Lesson for the simulator:** the daily-candle model is too pessimistic about intraday lows and too optimistic about stop and take-profit fills. Always confirm prop settings on hourly data.

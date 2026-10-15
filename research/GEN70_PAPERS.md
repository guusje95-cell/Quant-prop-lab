# Gen70: the four uploaded papers, exact full-text rules

Pre-registered in `config/gen70_protocol.json` before any number was computed. Script: `scripts/gen70_papers.py`; results in `results/gen70_papers.csv`; daily series in `results/cache_gen70_daily.parquet`. Trials added: 11 (Paper_4 was not in the upload and is not tested).

Data: Binance USD-M pack (20 coins, 5m klines incl. trade count and taker-buy volume, funding, metrics). Pass rule: TEST >= 0.8, HOLD >= 0.5, DEV > 0, corr with C* <= 0.3, and adding the sleeve to v4 must raise the 2022-26 Sharpe (v4 on the daily recipe: 1.94).

| Idea | DEV | TEST | HOLD | 2023+ | corr C* | corr v4 | v4 + it | Verdict |
|---|---|---|---|---|---|---|---|---|
| **W1 Weiss reversal, last Friday (PRIMARY)** | 0.47 | 1.64 | 0.62 | 1.14 | 0.00 | -0.02 | **2.29** | **passes the gate (weak evidence, see below)** |
| W2 every Friday | -0.17 | 1.53 | -0.40 | 0.59 | 0.00 | -0.03 | 1.95 | info only |
| W3 big pre-move days | -0.86 | 0.01 | -1.27 | -0.47 | 0.00 | -0.11 | 1.52 | info only |
| W4 every day (placebo) | -1.23 | -2.33 | -3.56 | -2.88 | 0.01 | -0.07 | 0.72 | placebo fails, as the paper predicts |
| A1 AdaptiveTrend, monthly selection (PRIMARY) | 0.55 | 0.44 | -1.15 | -0.22 | 0.61 | 0.25 | 1.40 | rejected |
| A2 AdaptiveTrend, fixed params | 1.38 | 1.15 | -0.88 | 0.27 | 0.66 | 0.36 | 1.63 | info only |
| D1 Dhanya own-history 11 books (PRIMARY) | 0.04 | 0.50 | 1.91 | 1.08 | -0.12 | 0.39 | 2.12 | rejected (TEST < 0.8) |
| D2 cross-sectional control | 0.89 | 0.48 | 1.44 | 0.86 | -0.05 | 0.39 | 2.11 | info only |
| D3 funding-rank book alone | 1.29 | 0.42 | 2.12 | 1.12 | -0.08 | 0.40 | 2.13 | info only |
| C1 CTREND CS-C-ENet (PRIMARY) | -0.73 | -1.61 | 0.24 | -0.80 | -0.03 | -0.03 | 1.45 | rejected |
| C2 CTREND naive combination | -0.36 | -0.50 | 0.05 | -0.26 | 0.03 | 0.01 | 1.64 | info only |

## What each paper gave

**Weiss et al. (option-expiry reversal).** The full-text rule is conditional: fade the 07:00-08:00 UTC move from 08:00 to 10:00, only on heavy-expiry days. Our proxy for heavy expiry is the Deribit monthly expiry (last Friday). It passes on all splits. The unconditional every-day version loses heavily, exactly as the paper reports (no effect in the full sample). That is a useful sign that the effect is tied to expiry and not a generic intraday reversal.

But the evidence is thin (post-hoc diagnostics, not used for selection):
- Only 81 events since 2020 (12 per year).
- Mean +0.25% per event (BTC/ETH average, after 2 x 5 bp), hit rate 64%, t = 1.60 (not significant on its own).
- Worst event -5.1%, best +6.3%.
- Positive in every year except 2020.
- The family has been tested before (Gen65 K2 fixed-direction, Gen69 forward-test note). Counting those, roughly 6 trials, so the multiple-testing bar is higher than t = 1.6.
- The portfolio gain is partly mechanical: equal risk gives this sparse sleeve 4x notional (10% vol from a 2.5%-vol stream). Capping its notional: cap 1.0 → 2.29, cap 0.5 → 2.20, cap 0.25 → 2.09. Max DD improves from -12.0% to -9.1/-9.9/-10.4%; worst portfolio day is unchanged (-3.8%).

**Decision:** W1 enters as a **v5 candidate at notional cap 0.5 per unit of portfolio** (Sharpe 2.20, max DD -9.9%). The cap is a risk choice taken because of the low t-stat, not a fitted optimum (cap 1.0 scores higher). It runs on paper first, alongside v4; it goes live only if forward events behave like the backtest. Execution is simple for a bot: once a month, read the 07:00-08:00 move and enter the opposite side at 08:00 for two hours.

**Bui & Nguyen (AdaptiveTrend).** The exact construction fails: HOLD -1.15, correlation with C* 0.61 (it is long-biased trend, the same bet as C*). Monthly grid re-optimisation makes it worse than fixed parameters, the opposite of the paper's claimed +1.07 Sharpe. The paper's own numbers are internally inconsistent: a 36-month OOS window shown to Oct 2025; a "+1.07" ablation gain that does not match its table. Rejected.

**Dhanya MD (every asset its own benchmark).** On 20 coins (4 per quintile book) the full 11-factor own-history construction scores TEST 0.50 and fails. Own-history ranking beats the cross-sectional control on 2023+ (1.08 vs 0.86) but not on DEV. The funding-rank book alone does as well as all 11 factors combined. So on our universe the paper's result is mostly the carry component it itself flags (Section 5.3), which we already hold as premium carry (corr v4 0.39). Rejected.

**CTREND (Fieberg et al., JFQA).** The exact combined elastic-net construction now works mechanically: on average 12.4 of 28 forecasts are selected, against all-zero in Gen57 B3. But it loses money on 20 liquid perps (TEST -1.61), and the naive combination also fails. The paper's effect comes from a 3,000-coin universe dominated by small caps; it does not carry over to the large perps a prop firm lets us trade. Rejected.

## Trial count
Gen70 adds 11 trials (4 primaries + 7 variants).

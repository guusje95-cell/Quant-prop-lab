# Audit of the "estimated live Sharpe" (v9.8), 2026-10-27

Script `scripts/v99/a1_methodology.py`, numbers `results/v99/a1_methodology.json`, cost numbers `results/gen473b.json`.
Input: the v9.8 paper code's own research-pack run (`results/v98_paper_sleeves.parquet`), daily returns 2022-01-01 .. 2026-09-30
(1,734 days).

## 1. Three different quantities
| Quantity | Value | What it is |
|---|---|---|
| Observed backtest Sharpe | **3.24** (95% CI 2.48-4.00; block bootstrap 5-95% 2.61-3.91) | in-sample statistic of one selected strategy |
| Execution-honest backtest | **3.28** realistic / 3.16 pessimistic (Bybit taker on NET trades) | same, with the costs the bot would pay |
| Selection-adjusted Sharpe | 1.67-2.72 depending on method (below) | an estimate that removes part of the selection luck |
| Future live Sharpe | unknown; plausible range below | depends also on decay, regime and execution, which no formula here measures |

## 2. The project method (reproduced)
`planning = SR_obs - E[max SR of N zero-edge trials]`, with
`E[max] = sqrt(1/T) * ((1-g) * Phi^-1(1 - 1/N) + g * Phi^-1(1 - 1/(N e)))`, g = Euler-Mascheroni, T = 1,734 days, annualised x sqrt(365).
N = 1,849 (the sum of `trials_added` over the 391 registered protocols; earlier generations without that field are not counted,
so 1,849 is if anything low): **planning 1.668** (N = 300: 1.91; N = 100: 2.08). Reproduces the 1.67 used.

Assumptions and limits:
- E[max] is the *significance threshold* of the Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014): the Sharpe the best of N
  worthless strategies would show by luck. DSR asks whether SR_obs beats it (here P = 0.99999 at N = 1,849: the edge is almost
  certainly real). **Subtracting the threshold from SR_obs is not part of DSR and is not an estimator of future Sharpe.** It
  amounts to assuming the full best-of-N luck is in this strategy on top of a real edge. It is a conservative heuristic.
- It treats the N trials as independent. They are not (many are variants of each other; in the 502-book family below the effective
  number of independent books is 5.5 out of 502). Correlated trials make E[max] smaller, so the haircut is too large. But N also
  understates the true search: many ideas were rejected in thought, from the literature, or before any protocol existed.
- Null variance 1/T is right for a zero-edge null (the skew/kurtosis terms vanish at SR = 0). Non-normality matters for the
  uncertainty of SR_obs: skew 2.5, kurtosis 19.6, SE 0.39. Daily autocorrelation is small (lag 2: +0.10); the Lo (2002) annualisation
  gives 3.31, so no inflation from autocorrelation.

## 3. Alternatives the data supports
| Method | Result at N = 1,849 | Assumption |
|---|---|---|
| Project (SR - E[max]) | **1.67** | all N trials independent, full best-of-N luck inside this strategy |
| Harvey & Liu (2015) haircut, BHY | **2.56** (Bonferroni 2.72) | multiple-testing adjusted t-stat (t = 7.06) mapped back to a Sharpe; independent tests |
| CSCV on the 502 sleeve-subset books | PBO **0.13**; in-sample winner 3.53 -> out-of-sample 2.88 (**decay 0.64**) | only the "which sleeves" choice, not the choice of the sleeves themselves |
| Recent period only | 2025: 2.57, 2026: 2.79 (2022-24: 3.06 / 3.69 / 4.12) | partly selected on as well (holdout reused many times) |

PBO 0.13 says the sleeve combination is not overfit (an in-sample-best combination usually stays above the median out of sample).
The 0.64 decay of a best-of-502 choice is a lower bound on the total selection decay, because the sleeves themselves were picked
from about 1,849 trials.

## 4. A defensible statement
- The edge is real with very high probability (DSR > 0.9999 even at N = 3,000; t = 7.1).
- Its future size is uncertain: selection-adjusted estimates range from about **1.7 (project, conservative) to about 2.6 (Harvey-Liu)**.
  The recent 2025-26 period runs at about 2.6-2.8 before any selection adjustment.
- Execution: realistic Bybit costs on the net book do not lower the Sharpe (3.28 vs 3.24), because the backtest charges every
  ensemble version and basket member separately while the bot nets them. Pessimistic spreads/impact: 3.16.
- None of these numbers is "the" live Sharpe. The only real measurement is the paper / live record, and 56 days give an SE of the
  annual Sharpe of about 2.6 (it proves the pipeline, not the edge).

## 5. Decision rule kept for v9.9
The **project method at N = 1,849 stays the gate** (conservative, consistent with all earlier decisions; not lowered to reach a target).
A v9.9 candidate reaches the target only if its **execution-honest** Sharpe minus E[max] at N = 1,849 (plus every trial added in
v9.9) is >= 2.0, i.e. an execution-honest backtest of about **3.57**. Harvey-Liu and CSCV are reported next to it for every candidate.
For reference, v9.8 under the same gate: 3.28 - 1.57 = **1.71**.

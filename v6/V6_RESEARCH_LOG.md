# V6 Research Log

Each entry records what was done, what was learned and what it changes next. Newest entries are at the bottom.

## 2026-10-09 · Entry 1 — Foundation and re-audit
* **Checks:** 75/75 tests pass. CT1 reproduces bit-exactly (`experiments/v4_ct1_evaluate.py`). Ledger hash chain intact.
* **Network:** only GitHub and PyPI are reachable (binance.vision, exchange APIs, HuggingFace and FRED return proxy 403). Installed from PyPI: lightgbm, hmmlearn, arch, ruptures.
* **New data:** `robcarver17/pysystemtrade` @bbe29e19 (GPL-3), 252 back-adjusted futures, 1970s → 2024-03-28, with carry contracts and spread-cost estimates. None of it has been used by this project before.
* **Status change:** CT1 mapped to **PROMISING_BUT_UNVALIDATED**. Its 2025–26 cross-asset confirmation failed and its BTC holdout is now contaminated. Recorded in the ledger.
* **Prior worth remembering:** v1 H9 (multi-asset daily TSMOM on Dukascopy CFDs, TRAIN 2013–18) was rejected after spread plus CFD financing. That window falls in the well-known 2011–18 trend drought, and CFD financing is far costlier than futures. It is not evidence against futures trend over decades.

## 2026-10-09 · Entry 2 — Why did CT1 decay? (`experiments/v6_ct1_decay.py`, `results/v6_ct1_decay.json`)
Seven competing explanations were checked on already-USED BTC data, so this is descriptive only.

| Explanation | Verdict | Evidence |
|---|---|---|
| E1 costs/funding grew | **No** | Cost drag 1.6 → 2.3% p.a.; funding −1.9% → −1.9% (−7.9% in 2020–21). The gross Sharpe falls just as much as the net (1.62 → 0.54). |
| E2 trend persistence weakened | **Partly, recently** | Variance ratios barely moved (VR60 1.16 / 1.13 / 1.20 / 1.09). TSMOM predictive t-stats: TRAIN 1.5–3.0, holdout −1.2–0.3 (short horizons ≈ 0). Signal flips per year 19 → 29 in 2024–26, i.e. more whipsaw. |
| E3 short side broke | **The short side never worked** | Short-leg Sharpe 0.05 / 0.09 / 0.03 / −0.25. All of CT1's profit came from the long leg (1.77 / 1.51 / 0.71 / 0.76). |
| E4 horizon shift | Mixed | No leg dominates after 2021. TSMOM120 led in OOS (1.08), TSMOM60 in the holdout (0.62). This looks like noise across legs, not a clean shift. |
| E5 vol regime / capped sizing | Minor | BTC vol 75 → 47%. Mean \|w\| rose 0.42 → 0.53 and time at the cap went to 10%. Realized strategy vol stayed at about 30%, roughly as targeted. |
| E6 fewer large trends | **Yes** | BTC drift/vol 0.83 / 1.15 / −0.08 / 0.50. The top 5% of days account for 38% → 178% of P&L, so the rest of the holdout lost money. |
| E7 noise / selection | Both contribute | Dev 1.46 vs post 0.43; 95% CI of the difference [−0.10, 2.25], P(no decline) ≈ 4%. CT1 was chosen from the best-looking family in TRAIN/VAL, so some shrinkage was expected. |

**Learning statement.** CT1 is best described as *conditional long exposure to BTC trends*: long when the trend is up, roughly flat on net otherwise. It is not a symmetric trend premium. Its returns scale with BTC's own drift and trendiness. These were extraordinary in 2015–21 and ordinary afterwards, and shorter-horizon persistence disappeared in 2024–26. Costs are not the problem.

**Consequences:**
1. A long/flat variant is the economically honest form. It cannot be validated on BTC because the data is used, so it is registered for the *prospective* paper trial only, as CT1-LF next to CT1 with the same signals and no re-tuning.
2. Whether trend is a cross-market premium must be answered on untouched data, which is the futures panel (Entry 3+).
3. Expect any crypto trend edge to stay small. Size the paper trial on the post-2021 distribution (already done: 0.30× book).

## 2026-10-09 · Entry 3 — Futures panel built (`src/qpl/data/futures_panel.py`)
* **Panel:** 252 instruments → 227 after de-duplication (mini/micro/duplicate venues collapsed by return correlation > 0.97, keeping the cheapest member) → **155 in the pre-registered universe**: 38 equity, 33 FX, 30 bond, 26 ags, 13 metals, 13 energy, 2 vol.
* **Exclusions:** sector and single-stock contracts; crypto (to keep the test independent of V4); and any instrument with cost/vol > 0.01, broken vol or stale data. Coverage grows from 16 instruments (1975) to 154 (2023).
* **Data defects found:** decimal-shift bad ticks (SUGAR_WHITE 1989, MSCIEAFA 2010 showed +900% days). Repaired with a spike filter (≥2.5× jump reverting next day). The repair uses t+1 and is documented. SUGAR_WHITE stays broken and is excluded by rule.
* **Return convention:** ΔADJ / PRICE(t−1), using the actual contract price because back-adjusted levels can be negative. Carry comes from the carry-contract spread.

## 2026-10-09 · Entry 4 — Generation 13 futures factors (`experiments/v6_futures_gen13.py`; protocol committed bb24d93 BEFORE any return)

| Family | DISCOVERY 1975–2004 | VALIDATION 2005–13 | TEST 2014–19 (1 look) | HOLDOUT 2020–24Q1 (1 look) | Status |
|---|---|---|---|---|---|
| F0 CT1 transfer (frozen crypto idea) | 1.16 | 0.34 | 0.60 | 0.51 | ELIGIBLE |
| F1 TSMOM 63/126/252 | 1.35 | 0.52 | 0.90 | 0.61 | ELIGIBLE |
| F2 EWMAC 4 speeds | 1.43 | 0.61 | 0.90 | 0.70 | ELIGIBLE |
| F3 Carry | 1.15 | 0.80 | 0.82 | 0.44 | ELIGIBLE |
| F4 XS momentum | 0.48 (0/1 neighbours positive) | – | – | – | REJECTED |
| F5 XS value | 0.19 | – | – | – | REJECTED |
| F6 Skew | −0.15 | – | – | – | REJECTED |
| F7 Combo (F0–F3, equal risk) | 1.51 | 0.63 | 0.96 | 0.70 | ELIGIBLE |

Long-only risk-parity benchmark, for reference, is reported in `results/v6_futures_gen13.json`. Residual Sharpe vs that benchmark ≈ net Sharpe, since betas are −0.2…0.3.

**Falsification audit** (`experiments/v6_futures_audit.py`):
* A1: pysystemtrade weekly returns correlate 0.89–0.99 with independent Dukascopy CFD/FX data. The data is real and correctly stitched.
* A2: the year pattern matches known trend-industry history (2008 +, 2011–13 ≈ 0/−, 2014 strongly +, 2022 +, 2023 −).
* A4: robust to execution lag 1–5 days.
* **Costs are the weak point.** At 3× the assumed costs, trend VALIDATION ≈ 0 and TEST ≈ 0.2; at 5×, all negative. Carry is the most cost-robust (3×: 0.52 / 0.29). EWMAC has the lowest trend turnover.
* A5: a random half of the universe still gives TEST 0.50–0.98, so the result doesn't depend on instrument choice.
* A3: P&L is broad (55–65% of instruments positive; top 5 = 20–30% of P&L). Bonds contributed most in 2014–19 and ags/energy in 2020–24.
* Gross notional leverage rises from 3–4× (pre-2004) to 7–17× (2014+) and turnover from 100 to 300× a year. Equal-risk sizing across many low-vol instruments, plus the book vol target, puts a lot of notional through costs.

**Learning statements:**
1. Trend and carry in diversified futures **replicate** in this untouched dataset, through two single-use looks. This is confirmation of well-published effects, not discovery (knowledge caveat in the protocol).
2. The frozen crypto CT1 idea transfers out of domain (0.60 / 0.51 net on TEST / HOLDOUT). Trend persistence is a cross-market effect, which makes the BTC result more credible, but the BTC-specific decay (Entry 2) still stands.
3. Cross-sectional momentum, value and skew did **not** survive costs in futures. XS momentum's gross 1.05 was eaten by 5.7% annual costs.
4. The binding constraints are now **costs/turnover and implementability**: contract granularity, capital, and leverage of 7–17× notional. The futures TEST/HOLDOUT periods are now USED. Further confirmation must be prospective, or must come from cost/implementation realism checks that don't re-select signals.

## 2026-10-09 · Entry 5 — Gen14 implementation research (`experiments/v6_futures_gen14.py`, protocol `config/v6_gen14_protocol.json`)
* **Buffering (G14a).** Carver-style no-trade bands cut turnover 185 → 60 (F7) and roughly halve cost sensitivity. F7 VALIDATION at 3× costs goes 0.16 → 0.28 (b = 0.05) and → 0.62 (b = 0.4). The pre-registered smallest-b rule adopted **b = 0.05 for F7** and **b = 0.10 for F2 EWMAC**. Larger b looked better still, but adoption followed the rule.
* **Leverage caps (G14b).** Capping gross notional at 6–8× costs about 0.0–0.3 Sharpe in 2014–24 (contaminated-secondary) and binds on 43–64% of days. The low-vol bond/STIR legs drive the leverage.
* **Capital (G14c), integer contracts with the smallest available contract.**

  | Capital | Instruments held (2020–24) | VALIDATION Sharpe | 2014–24 Sharpe (contaminated) | Realized vol |
  |---|---|---|---|---|
  | $100k | 2 | 0.05 | 0.50 | 2.6% |
  | $250k | 13 | 0.53 | 0.60 | 5.5% |
  | $1M | 52 | 0.77 | 0.84 | 8.8% |
  | $5M | 105 | 0.57 | 0.89 | 10.7% |

  The continuous-weight book is 0.60 / 0.83.
* **Audit V6-B1 (two bugs in G14c, both fixed and logged; the superseded numbers are kept in the JSON):**
  1. The band was coded as max(0.5, 10%) instead of the protocol's 0.5 + 10%.
  2. **Exchange holidays left NaN contract notional**, which zeroed the target and forced round trips. This made the first run show Sharpe < 0 even at $5M. The main engine was checked and is unaffected (4 dropout cells in total).
* **Learning:**
  * The diversified futures book is implementable at about **$1M+**. At $250k it under-deploys risk (5.5% vol) with about 13 instruments.
  * Below about $250k, a different design is needed: a small, hand-picked, micro-contract universe. This becomes hypothesis G15-SMALL, which must be selected without performance data.
  * Futures prop firms (intraday-flat rules) remain incompatible with multi-day trend/carry.

## 2026-10-09 · Entry 6 — Gen15 adaptive layers (`experiments/v6_gen15_regime.py`, `v6_gen15_ml.py`; protocol d8b1625)
Out-of-sample = annual walk-forward 1995–2013. 2014–24 is contaminated-secondary.

| Layer | WF OOS Sharpe | Baseline | Random p95 / bootstrap | 2014–24 (contaminated) | Verdict |
|---|---|---|---|---|---|
| B0 = 50/50 equal-risk TREND + CARRY sleeves | 1.34 | – | – | 0.90 | baseline |
| H15a 2-state HMM regime weights (forward filter) | 1.37 | 1.34 | 1.39 | 0.88 | REJECTED |
| H15b BOCPD de-risking | 1.37 | 1.34 | 1.38 | 1.00 | REJECTED |
| H15c factor momentum (Ehsani–Linnainmaa) | 1.39 | 1.34 | 1.41 | 0.96 | REJECTED |
| H15d ridge on 15 features | 0.99 | F7 1.09 | P(≤F7) 0.73 | 0.71 | REJECTED |
| H15d LightGBM | 1.14 | F7 1.09 | P(≤F7) 0.38 | 0.69 | REJECTED |

**Learning:**
1. Regime, change-point and factor-timing layers add nothing beyond what random weight paths with the same distribution achieve. This is the third independent replication of that finding (v3 futures filters, V4 crypto funding filter, now here). Timing is not where the edge is.
2. ML does not extract incremental information from trend/carry/vol/skew features beyond the simple equal-weight combination. LightGBM leans most on sigma, sig_ratio and skew, which are risk features, not direction. Ridge assigns alternating signs to correlated EWMAC speeds, a sign of collinearity, not of new information.
3. **Construction matters more than timing.** Equal risk across *sleeves* (trend vs carry, correlation 0.44 OOS / 0.25 later) gives 1.34 OOS against 1.09 for signal-level averaging (F7, where trend gets 3/4 of the signal weight). Within the protocols this is an observation: B0 was a baseline, not a pre-registered candidate. It becomes candidate **F9_SLEEVE_RP** for prospective validation, with no further historical selection possible.

## 2026-10-09 · Entry 7 — Statistical integrity of the futures survivors (`experiments/v6_futures_stats.py`)
* **CSCV PBO = 0.017** over the full 26-config gen13 grid (1985–2013, 12,870 splits). The in-sample winner never lost out of sample; median OOS Sharpe of the IS winner is 1.08. Selection *within* the grid is not overfit, mostly because every trend/carry variant works.
* **Honest futures trial count: 42.** That is the 26-config gen13 grid plus the gen14 and gen15 variants.
  * Full-sample DSR (1985–2024): F7 0.79, F2 0.73, F3 0.72, sleeve-RP B0 0.96.
  * Post-2014 only: 0.37 / 0.32 / 0.15 / 0.45.
* **Per-window significance is weak.** Block-bootstrap 95% CIs of the HOLDOUT Sharpe span zero (F7 −0.22…1.56), Newey–West p is 0.08–0.18, and no family survives Holm in TEST or HOLDOUT alone. The pre-registered gates were sign-based (net > 0 and residual > 0), and they passed. Significance comes from the long sample (DISCOVERY CI 1.16–1.87), not from the recent windows.
* **MinTRL** (Bailey & López de Prado) for rejecting SR ≤ 0 at 95% with the observed skew/kurtosis: SR 0.5 → **10.6 years**, SR 0.7 → 5.4 years, SR 1.0 → 2.6 years.

**Learning:**
* The "ELIGIBLE" status is honest about direction and robustness, but not about the post-2014 *size* of the edge. A realistic expectation for a costed diversified trend+carry book is **SR 0.5–0.8 with wide uncertainty**.
* A prospective paper track cannot statistically confirm such an edge in under about 5–10 years. Prospective trading is therefore a *safety and implementation* check (does the live book behave like the backtest?), not a significance test. Decisions must rest on the 50-year cross-market evidence plus economic rationale, with sizing set by the lower part of the uncertainty band.

## 2026-10-09 · Entry 8 — Crypto CT1 inside a futures trend+carry portfolio (`experiments/v6_portfolio.py`; descriptive, all data USED)
* **Correlations (weekly, 2015–2024Q1):**
  * CT1 vs B0 (futures sleeve-RP) 0.09; vs TREND 0.15; vs CARRY 0.00; vs long-only RP −0.02.
  * In B0's worst 10% of weeks, the CT1/B0 correlation is −0.00 (no tail co-movement).
  * In the long-only benchmark's worst 10% of weeks, TREND averages +0.32σ and CT1 +0.28σ (crisis-convex), while CARRY averages −0.14σ.
* **Adding CT1 at 1/3 of the risk:** Sharpe 0.63 → 1.09 and max DD −14% → −10% (2015–24). Bootstrap gain +0.46, 90% CI [0.23, 0.70].
* **Caveat:** CT1's 2015–21 Sharpe (1.3–2.6 per year) drives most of that gain. Using CT1's post-2021 Sharpe of about 0.4, the expected gain at 1/3 risk is roughly +0.1. That is still positive because of the near-zero correlation, but modest.
* **Learning:** the best use of CT1 is as a *small diversifying sleeve* next to a diversified futures trend+carry core, not as a standalone strategy. Allocation should follow conservative SR assumptions: about 0.4 for CT1 and 0.5–0.7 for the futures core.

## 2026-10-09 · Entry 9 — New crypto data: Coin Metrics community (`experiments/v6_gen16_crypto_xs.py`; protocol 5373c4f)
* **Data:** `coinmetrics/data` @f1a36afb (CC BY-NC 4.0, research use only). 139 assets with prices, including some dead coins (VTC, PPT, HUSD…), so survivorship is reduced but not eliminated. 81 assets remain after removing stablecoins, wrapped tokens and duplicate deployments. The universe is point-in-time: top 30 by market cap with a volume filter, rebalanced weekly with a 1-day lag and 30 bp costs.

| Hypothesis | TRAIN 2017-07..2020 net (gross) | Neighbours | Verdict |
|---|---|---|---|
| H16a XS momentum 21d | 0.25 (0.61) | 7d 0.11, 63d −0.21 | REJECTED |
| H16b XS reversal 7d | −1.27 (−0.69) | 3d −0.86, 14d −1.27 | REJECTED (sign opposite: weekly *continuation*) |
| H16c XS on-chain value (−log MVRV) | −0.29 (−0.15) | z-score −0.21 | REJECTED |
| H16d XS network growth (active addresses) | −0.26 (0.23) | 91d −0.07 | REJECTED |
| H16e BTC MVRV timing | 0.48, residual vs B&H **−0.37** | scaled 0.89 / −0.40 | REJECTED (just a lower-beta BTC) |

**Learning:**
1. Within a curated top-30 alt universe, the published crypto cross-sectional factors (momentum, on-chain value, network adoption) do not survive realistic weekly costs in 2017–2020. Gross XS momentum of 0.6 is consumed by 1.5× weekly turnover at 30 bp.
2. On-chain valuation (MVRV) is not a timing edge once BTC beta is removed.
3. Weekly reversal comes out strongly negative, i.e. short-term continuation. That would be a *new* hypothesis built on TRAIN evidence, so it is logged as a backlog idea (needs lower-turnover construction), not rescued.
4. The only crypto edge in the whole project remains time-series trend on the majors (CT1), and it behaves as conditional beta (Entry 2).

## 2026-10-09 · Entry 10 — Small accounts (`experiments/v6_gen17_small.py`, protocol committed before the run)
* **Selection:** a non-performance Carver-style minimum-capital rule. Risk per contract (notional × vol) must be ≤ capital × 5% / K, filled round-robin across six classes.
* **$100k → K = 5** (SGX Nikkei, Schatz, CAD micro, Corn mini, Euribor). Integer VALIDATION 0.56, DISCOVERY 0.61, 2014–24 0.61 (contaminated). **Passes the gate**, but only 4 instruments existed in 2005.
* **$250k → K = 11**, six of them FX micro-contracts. Integer VALIDATION 0.33 → **REJECTED**; continuous 0.32, so the failure is not caused by rounding.
* **Learning:** at small capital, the affordable set is dominated by low-risk-per-contract short-rate, bond and FX micro-contracts. Diversification collapses and results become noise-dominated: the "better" $100k result next to a failing $250k result is the signature of noise. **A faithful trend+carry book needs about $1M.** Below that, the honest options are:
  1. accept a concentrated, noisy book;
  2. use the crypto CT1 sleeve, which is divisible;
  3. wait. A ledger note records that G17_SMALL_100K is not recommended despite passing the gate.

## 2026-10-09 · Entry 11 — Has the trend premium decayed? (`experiments/v6_trend_decay.py`; descriptive, all periods)

| Sleeve | 1980s | 1990s | 2000s | 2010s | 2020s | Slope / decade (HAC t) | PELT break | pre-2010 → post-2010 |
|---|---|---|---|---|---|---|---|---|
| TREND | – | – | 1.16 | 0.48 | 0.60 | see JSON | 2004 | 1.24 → 0.57 |
| CARRY | 1.07 | 1.26 | 1.23 | 1.05 | 0.21 | −0.20 (−1.9) | 2014 | 1.24 → 0.78 |
| B0 (sleeve-RP) | 1.34 | 1.34 | 1.36 | 0.94 | 0.57 | **−0.21 (−2.9)** | 2004 | 1.48 → 0.84 |

TSMOM by asset class and decade: FX trend collapsed (1.42 → 0.22 → −0.17); equity trend ≈ 0 since 2010; bonds held up (0.80 in the 2010s); ags and energy revived in the 2020s (0.94 / 0.87).

**Learning:**
1. **CT1's decay is part of an economy-wide decline in trend and carry premia since ~2005–2010.** That is consistent with post-publication decay and crowding (McLean & Pontiff 2016; the CTA industry's AUM growth). It is not only a crypto quirk.
2. Forward expectations should be anchored on post-2010 levels: **SR ≈ 0.5–0.8 for diversified trend+carry, and possibly lower** if the slope continues. The F9 monitoring expectation (SR 0.5) is set accordingly.
3. Diversification across asset classes is what keeps the book alive. No single class has been reliable in every decade. This argues against small, concentrated books (Entry 10).

## 2026-10-09 · Entry 12 — Gen18 crypto XS continuation with turnover control (`experiments/v6_gen18_crypto_cont.py`)
* **Design:** a new hypothesis from gen16 evidence (7-day continuation), rebalanced every 4 weeks. Judged on VALIDATION 2021–22 and TEST 2023–26 only.
* **Results:**
  * VALIDATION: net **0.53** (gross 0.73). Neighbours: 14-day signal 0.43, 2-weekly rebalance −0.75. Passed the "≥ 1/2 neighbours" gate.
  * TEST (single look): net **0.01** at 30 bp, −0.25 at 60 bp → **EXPLORATORY**.
  * For information, the same rule's TRAIN 2017–20 is −0.56.
* **Learning:** the alt cross-sectional continuation effect flips sign across periods and is very sensitive to rebalance frequency. That is no edge after costs. Crypto cross-sectional research on this curated universe is closed until a survivorship-free, executable dataset exists (data backlog #2).

## 2026-10-09 · Entry 13 — Stopping point for this session
The research queue reachable with GitHub/PyPI-only data has been worked through. What remains needs one of:
1. prospective or post-2024 futures data for the F9 paper book;
2. Binance public data (survivorship-free universe, perp basis, executable prices);
3. order-book, options or macro-event data;
4. measured fills for cost calibration.

The repository is clean and resumable (`v6/V6_NEXT_ACTIONS.md`). Report: `reports/v6_research_report.html`.

## 2026-10-10 · Entry 14 — Master mission batch 1: HTF liquidity levels (Track A)
* **Baseline re-established:** V6 F7 re-run reproduces 1.513 / 0.629 / 0.956 / 0.697 exactly. pysystemtrade `SpreadCost` is a **half-spread per trade** (`docs/production.md`), so V6 cost accounting is correct.
* **gen19 (1-hour bars, previous day/week levels; 13 Dukascopy CFD/FX + BTC), protocol 701cd5b: 12/12 REJECTED at DEV.**
  * Sweep and reclaim has a real but small **gross** edge (+0.06R, gross Sharpe 1.17 on 4,409 trades). Costs on tight hourly stops (~0.1R per trade) flip it to −0.69.
  * Hourly breakouts lose even gross.
* **gen20 (daily bars, previous week/month levels), protocol 09761e9.**
  * CFD/FX: all REJECTED at DEV. Near misses: monthly sweep-reclaim 0.34 (MTM 0.55, 46% breadth) and monthly failed breakout 0.44.
  * BTC weekly-level breakout passed DEV / VAL / TEST: 0.88 / 0.75 / 0.86 (MTM 0.89 / 0.72 / 1.21), 2× cost 0.77, shorts positive, beta to BTC ≈ 0, corr 0.36–0.55 with CT1. Status corrected from the code's ELIGIBLE to PROMISING (no fresh holdout; BTC path previously seen).
* **Measurement fix:** `daily_series` booked a whole trade on its exit day. That is fine for sub-day holds but wrong for vol, beta and correlation of multi-day trades. `htf.core.daily_mtm` added, tested (sums exactly to trade R), and used for all daily-bar diagnostics. No gate decision changes.
* **Cross-coin transfer (single use, protocol committed first):** 11 mirror coins 2017–2023, pooled 0.62, 2× cost 0.47, 64% of coins positive → **PASS**. Robustness: ex-DOGE 0.36, ex-2021 0.28; 2019 −0.42, 2022 0.11.
* **Learning:**
  1. "Liquidity sweep" reversals at HTF levels are real in gross terms at the 1-hour scale but too small for retail costs. On daily bars they are weak and not broad.
  2. Breakouts of HTF levels only work where trends are strong (crypto). That is the same trend premium as CT1/F7, expressed through levels, not a separate liquidity edge.

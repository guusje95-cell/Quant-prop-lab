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

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

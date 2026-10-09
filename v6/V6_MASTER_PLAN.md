# V6 Master Plan — Quant Prop Lab

Started 2026-10-09. Branch `claude/autonomous-prop-quant-research-191f8d`. V1–V4 artifacts are preserved and not rewritten.
State lives in the hash-chained ledger (`research_database/ledger.jsonl`), the SQLite registry, `results/`, and the
`v6/` documents (regenerate the registry with `python scripts/v6_registry.py`).

## 1. Where V6 starts (evidence, not hopes)
* **Futures intraday (v1/v3):** 22 families; nothing better than EXPLORATORY. No untouched historical futures/FX/CFD data is left in the old sources.
* **Daily multi-asset TSMOM on CFDs (v1 H9):** rejected. TRAIN 2013–18 net −0.25…0.11 after spread and financing.
* **Crypto (V4):** one weak survivor, CT1. BTC Sharpe went 1.51 → 1.28 → 0.57 → 0.34 (TRAIN → VAL → OOS → holdout). It passed on ETH and failed on 21 perps 2025–26. **BTC 2024-01..2026-10 is now USED** and is never again a pristine holdout.
* **Environment:** only GitHub and PyPI are reachable (exchange APIs, vendors, HuggingFace, FRED and firm websites are blocked). Nothing is purchased.

## 2. The central research question for V6
> Is the only surviving idea, trend persistence, a real cross-market risk premium/behavioural effect that has merely
> weakened (and may be timed, diversified or better constructed), or was CT1 a crypto-specific artefact of the 2015–21 bull cycle?

Most of V6's information gain comes from answering this with **new, untouched data**: 252 back-adjusted futures markets
1970s→2024-03 from the pysystemtrade repository. They are new to this project, independent of all crypto data, and cover
four asset classes and many regimes.

## 3. Priorities (ranked by expected information gain × testability × data quality)
1. **CT1 decay diagnosis** (crypto data, descriptive). Decompose into persistence, costs, funding, long/short legs, signal horizon, volatility regime and exposure.
2. **Futures panel ingestion and audit.** Roll-adjustment sanity, gaps, costs from `spreadcosts.csv`, point-in-time universe.
3. **Pre-registered transfer test of the frozen CT1 rule to futures.** The rule is not re-tuned; this is out-of-domain confirmation of the *idea*.
4. **Futures factor families** with economic rationales, run in parallel:
   * time-series trend (multi-horizon)
   * carry (from the carry contract)
   * cross-sectional momentum within asset class
   * long-horizon reversal / value proxy
   * volatility-managed exposure
   * trend × volatility-state interaction
   * skewness
5. **Regime and adaptive layers** (HMM, Bayesian online change-point, volatility states). Each is tested only as a forward-looking filter against random-skip and unfiltered baselines, with nested walk-forward.
6. **ML layer** (regularised linear, gradient boosting) on the trend/carry/vol feature panel. It must beat the simple equal-weight factor baseline under nested walk-forward; otherwise it is rejected.
7. **Portfolio construction.** Risk parity and shrinkage across surviving sleeves, crypto CT1 included; marginal contribution; tail dependence.
8. **Crypto continuation**, only where data allows something new: a survivorship-free universe if a GitHub source exists, spot vs perp, and weekend structure.
9. **Data-acquisition backlog** for blocked research: order books, macro events, options.

## 4. Evaluation-period protocol (futures panel)
Written before any futures return was computed.

| Class | Period | Use |
|---|---|---|
| DISCOVERY | first data → 2004-12-31 | free exploration, parameter choice |
| VALIDATION | 2005-01-01 → 2013-12-31 | gate 2; family-level selection |
| TEST | 2014-01-01 → 2019-12-31 | one look per frozen candidate |
| PROTECTED HOLDOUT | 2020-01-01 → 2024-03-28 | one look per frozen candidate, after TEST pass |
| LATE HOLDOUT | TopstepX GC, SI, CL, 6E, 6B, 6J 2025-03 → 2026-04 (never used by a strategy) | optional single look, very short |

Knowledge caveat (recorded): the researcher knows the broad history of trend-following, including 2008 crisis alpha, the
2011–18 drought and the strong 2022. The protocol therefore freezes rules *before* looking, uses rules drawn from the
literature rather than invented ones, and treats TEST/HOLDOUT as confirmation of a published effect, not as discovery.

## 5. Decision rules and statuses
* **REJECTED:** fails its pre-registered gate, or is indistinguishable from its baseline or random control.
* **EXPLORATORY:** passes DISCOVERY but not VALIDATION, or has data-quality limits that cap it.
* **PROMISING BUT UNVALIDATED:** passes DISCOVERY and VALIDATION and is robust to neighbours and costs, but the TEST/HOLDOUT look is still pending or mixed.
* **ELIGIBLE FOR INDEPENDENT VALIDATION:** passes all pre-registered historical gates, including one protected-holdout look, with honest multiple-testing accounting. Next step is prospective paper trading. This is **not** deployment authorisation.

Legacy statuses map as follows:
* REJECT → REJECTED
* EXPLORATORY → EXPLORATORY
* VALIDATION_CANDIDATE → PROMISING BUT UNVALIDATED
* PAPER_TRADING_CANDIDATE (CT1) → ELIGIBLE FOR INDEPENDENT VALIDATION in name, but downgraded to PROMISING BUT UNVALIDATED because its 2025–26 cross-asset confirmation failed and its holdout is now contaminated. Recorded as a decision in the ledger.

Hard rules:
* Never re-tune on a period that has already been looked at.
* A changed hypothesis is a new hypothesis id with its own rationale.
* Gates are written in `config/v6_*_protocol.json` before results are computed.
* Count every variant.
* Report the leaderboard including failures.

## 6. Loop (each batch)
1. Review `v6/V6_RESEARCH_LOG.md` and the backlog.
2. Pre-register the hypotheses and gates in config.
3. Run, with baselines and random controls.
4. Record in the ledger.
5. Write a learning statement in the log.
6. Update `V6_RESULTS.md` and `V6_NEXT_ACTIONS.md`.
7. Regenerate the registry.
8. Commit and push.

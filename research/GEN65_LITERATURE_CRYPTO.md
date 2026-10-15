# Gen65: literature-based crypto ideas (2026-10-15)

**Sources:** `research_notes/Crypto strategy papers 2/` (two scans; abstracts only, because full texts were blocked).
**Protocol:** `config/gen65_protocol.json`. **Script:** `scripts/gen65_crypto.py`.

| Idea | DEV | TEST | HOLD | 2023+ | 2022 | corr C* | Portfolio 2022–26 (now 1.56) | Verdict |
|---|---|---|---|---|---|---|---|---|
| K1 own-history z of 30d momentum, XS (SSRN 7301919, unverified) | 0.34 | 0.81 | -0.20 | 0.40 | -2% | 0.06 | 1.55 | rejected |
| K1 variant: own-history z of premium | 0.19 | -0.41 | 0.87 | 0.12 | -26% | 0.02 | 1.17 | rejected |
| K2 Friday expiry window, last Friday (Weiss et al., FRL 2026) | -0.24 | 1.16 | 0.41 | 0.85 | 0% | 0.00 | 1.70* | fails (DEV, HOLD) |
| K2 variant: every Friday | -0.45 | 0.46 | -0.57 | -0.01 | | | 1.08 | rejected |
| K2 variant: last Friday, maker | -0.09 | 1.41 | 0.75 | 1.13 | +1% | 0.00 | 1.85* | near-miss (DEV slightly < 0) |
| K3 6h trend, ATR stop, monthly top-5, 70/30 (Bui & Nguyen 2026) | 1.19 | 1.77 | 0.52 | 1.19 | 0% | **0.59** | 1.62 | fails (corr 0.59) |

\* **Caution:** the expiry trade fires only 12 times a year. Scaling such a sparse series to the same volatility as the other sleeves puts a lot of leverage on very few trades, about 80 events in total. Its portfolio effect is therefore not reliable. It is also only the calendar part of the paper: the paper's conditioning on options open interest and dealer gamma needs Deribit options data we do not have.

**6h trend with coin selection:** works well on its own (2023+ 1.19, 2025–26 still 0.52). But it is largely the same trend exposure as C*, with correlation 0.59, so it adds little (+0.06).

## Verdict

Nothing passes the pre-registered criteria.

Two leads for forward testing only:
- the monthly-expiry window with maker orders;
- the 4h trend near-miss (Gen63).

Across Gen62–65, 30 crypto configurations were tested. One idea was added (premium carry, Gen61). The rest were rejected or are near-misses. Diminishing returns are clear: the remaining "improvements" are mostly within the noise you would expect from this many trials.

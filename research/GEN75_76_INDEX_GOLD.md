# Gen75-76: more index / gold / EURUSD ideas for CFD firms

- **Protocols:** `config/gen75_protocol.json` and `config/gen76_protocol.json`, both registered before their results.
- **Scripts:** `scripts/gen75_cfd.py`, `scripts/gen76_cfd.py`.
- **Data:** Dukascopy hourly, 2013-01..2026-09.
- **Costs:** 1 bp per side for indices and EURUSD, 2 bp for gold, 3%/yr financing per night held.
- **Trials added:** 14.
- **Pass rule:** TEST >= 0.8, HOLD >= 0.5, DEV > 0, and the sleeve must raise the CFD portfolio (Gen74: C* + Weiss, Sharpe 1.50).

| Idea (paper) | DEV 13-19 | TEST 20-23 | HOLD 24-26 | All | CFD portfolio + it | Verdict |
|---|---|---|---|---|---|---|
| H1 RSI(2) pullback in an uptrend, 4 indices (Connors) | 0.24 | 0.39 | 1.29 | 0.49 | 1.73 | fails TEST (near miss) |
| H1 variant RSI(2) < 5 | 0.32 | 0.30 | 1.34 | 0.49 | 1.78 | info |
| H2 pre-FOMC drift, US500 + US100 (Lucca & Moench) | 0.16 | 1.15 | 0.38 | 0.62 | 1.80 | fails HOLD (near miss; 107 events) |
| H2 variant to 16:00 ET | 0.09 | 0.73 | -0.40 | 0.24 | 1.18 | info |
| H3 gold PM-fix dip (Caminschi & Heaney) | -1.39 | -1.72 | -1.24 | -1.45 | -0.07 | rejected (costs of a daily round trip exceed the effect) |
| H3 variant AM fix | -3.35 | -3.63 | -2.80 | -3.22 | | rejected |
| H4 Asian-range breakout, EURUSD + gold | -0.86 | -0.36 | 0.28 | -0.46 | 1.08 | rejected |
| H5 vol-managed US500 + US100 (Moreira & Muir) | 0.69 | 0.88 | 0.91 | 0.80 | 1.51 | rejected: does not beat buy-and-hold in HOLD (1.03), adds nothing |
| O1 option-expiry week long (Stivers & Sun) | 0.79 | -0.53 | 0.09 | 0.10 | 0.80 | rejected (decayed after 2019) |
| O1 variant short the week after | -0.78 | -0.70 | -1.32 | -0.81 | | rejected |
| O2 cross-index weekly reversal | -0.08 | -0.18 | -0.18 | -0.14 | 1.01 | rejected |
| O2 variant 2-week ranking | -0.33 | -0.51 | 0.13 | -0.30 | | rejected |

## Reading
- **Gen73-76 together:** 19 published index / gold / FX timing ideas tested on 2013-2026 CFD data with realistic costs. None passes. The usual pattern is that the effect is visible in the paper's own era, then decays or is eaten by CFD costs.
- **Two near misses fit well with the crypto CFD book** (correlation about 0):
  - **RSI(2) pullback:** strong 2024-26, weak 2020-23;
  - **pre-FOMC drift:** strong 2020-23, weaker 2024-26.

  Each raises the CFD portfolio Sharpe from 1.50 to 1.73-1.80. They fail the registered rule, so they are **not adopted**. Promoting them now, after seeing these numbers, would be exactly the overfitting we avoid. They go on the forward-test list: they can run in paper mode next to v5 and be judged on new data.
- **What could still work for CFD firms:**
  - non-index assets that are arriving now: FX majors (the FX fix pattern, Gen60 D1), commodities, more indices (multi-asset trend re-test);
  - futures-firm versions of the index ideas, with lower costs (Databento);
  - the crypto CFD book (Gen74), which already works.

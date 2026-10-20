# Gen124-126 (2026-10-20): intraday futures on Databento 1-minute ES/NQ

## Gen124: news-minute continuation and gap fade (rejected)
| Test | CFD 5m (1 bp) | Futures 1m (1 tick + commission) |
|---|---|---|
| J1 08:30 ET continuation | 0.76 / -0.60 / -0.84 | 0.54 / -0.31 / -0.73 |
| J2 14:00 ET continuation | -0.82 / -0.81 / -0.11 | -0.81 / -0.82 / 0.03 |
| J3 RTH gap fade (> 0.4%) | 0.92 / -1.08 / 0.82 | 0.82 / -0.98 / 0.76 |

The two data sources agree closely, which is a good check of both datasets and the engine. Splits: 2018-20 / 2021-23 / 2024-26.

## Gen125: real-futures retest of the intraday near-misses
- **Costs (median 2018-26), 1 tick + $0.85 micro commission per side:** ES 1.01 bp, NQ 0.49 bp. At half a tick: ES 0.71, NQ 0.40.

| Test | DEV | TEST | HOLD | Verdict |
|---|---|---|---|---|
| **K1 noise-area breakout, ES+NQ (registered primary)** | 0.92 | 1.17 | **0.16** | **rejected (HOLD < 0.3)** |
| K1 component NQ | 1.05 | 1.07 | 0.88 | (component) |
| K1 component ES | 0.63 | 1.06 | -0.77 | (component) |
| K1 at half-tick cost (report only) | 1.04 | 1.31 | 0.31 | - |
| K2 5-minute ORB, ES+NQ | 0.27 | 0.56 | -0.66 | rejected |
| K3 month-end pension rebalancing (ES, 2010-26) | 0.45 | 0.05 | 0.81 | rejected |

- **NQ noise-area component:** about 11.4% a year at 11.4% vol, max DD -8.6%. Yearly Sharpe 2018 2.42, 2019 -0.31, 2020 0.49, 2021 0.88, 2022 1.22, 2023 1.09, 2024 1.20, 2025 0.31, 2026 1.37.
  - Correlation with v6 is 0.05, with the ES component 0.69.
  - Flat by 16:00 ET, so it is Topstep/Lucid compatible.
- **ES decays from 2024.** NQ holds up.
- **Choosing NQ after this result is selection.** Hence Gen126.

## Gen126: out-of-sample check on NQ 2010-2017 (pre-registered; data pending)
- **Protocol:** `config/gen126_protocol.json`. It needs the 2010-06..2017-12 NQ 1-minute file, a cost check of about $10 on the user's Databento credit.
- **Pass rule (all three):** Sharpe >= 0.5 over the whole period, positive in both halves, and positive in the fully unseen 2010-06..2013-07.

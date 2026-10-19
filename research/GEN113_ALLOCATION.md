# Gen113 (2026-10-19): sleeve allocation variants, all rejected (4 trials)

Protocol: `config/gen113_protocol.json` (registered before any number). Script: `scripts/gen113_alloc.py`. Results: `results/gen113.csv`.

The question: can a smarter way of weighting the sleeves raise the book Sharpe? Every variant is point-in-time (monthly, past data only) and keeps the same live-sleeve rules, the level multiplier and the 30-day vol targeting. Rule: the book's 2022-26 Sharpe rises AND its TEST and HOLD do not fall.

| Variant | v6 2022-26 | v6 DEV / TEST / HOLD | bf 2022-26 | bf DEV / TEST / HOLD | Verdict |
|---|---|---|---|---|---|
| P1 equal risk, 365d (current) | **2.46** | 1.61 / 3.44 / 1.90 | **2.25** | 1.15 / 3.45 / 1.55 | baseline |
| A1 ERC, Ledoit-Wolf (primary) | 2.33 | 1.66 / 3.16 / 1.88 | 2.13 | 1.16 / 3.23 / 1.46 | rejected |
| A2 min-variance | 2.11 | 0.91 / 2.87 / 1.95 | 1.88 | 0.96 / 2.86 / 1.29 | rejected |
| A3 inverse vol, 90d | 1.82 | 1.58 / 1.90 / 2.02 | 1.91 | 1.21 / 2.75 / 1.44 | rejected |
| A4 half Sharpe tilt | 2.06 | 0.68 / 3.16 / 1.88 | 1.91 | 0.64 / 3.28 / 1.31 | rejected |

Reading: the sleeves are already nearly uncorrelated, so correlation-aware weights add estimation noise and nothing else. Faster windows and tilting towards recent winners both hurt. **The simple P1 equal-risk weights stay.**

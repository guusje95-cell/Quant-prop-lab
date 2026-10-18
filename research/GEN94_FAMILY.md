# Gen94: bounce-family ensemble and a 4-hourly bounce check (2026-10-18)

- **Protocol:** `config/gen94_protocol.json`, registered before any number. 2 trials.
- **Script:** `scripts/gen94_family.py`.
- **Both tests are replacements** for the H4 deleveraging-bounce sleeve: H4 alone is DEV 2022 0.70, TEST 1.00, HOLD 0.61. The Gen90 CFD book is 1.797.

| Test | DEV | TEST | HOLD | Book after | Verdict |
|---|---|---|---|---|---|
| F1 ensemble of all 6 registered bounce rules (H4, dip, DVOL, volume, discount, funding flush) | 0.60 | 0.49 | 0.33 | 1.27 | rejected: the weak legs dilute H4 |
| F2 bounce checked every 4 hours (48h hold) | 0.17 | 1.76 | 0.26 | 1.67 | rejected: HOLD worse |

**Legs on their own, 2020-22 / 2023-24 / 2025-26:**

| Leg | 2020-22 | 2023-24 | 2025-26 |
|---|---|---|---|
| H4 | 0.48 (zeros before 2022-12) | 1.00 | 0.61 |
| dip | 0.52 | -0.09 | 0.26 |
| DVOL | 0.12 | -0.35 | -0.49 |
| volume | 0.42 | 0.40 | 0.78 |
| discount | 0.63 | -0.47 | -0.09 |
| funding flush | 0.28 | 1.15 | 1.26 |

**Conclusion:**
- The daily H4 rule stays as registered.
- Of the bounce family, only open-interest deleveraging carries a robust edge.

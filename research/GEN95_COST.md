# Gen95: CFD cost structure (2026-10-18)

- **Protocol:** `config/gen95_protocol.json`, registered before any number. 3 trials.
- **Script:** `scripts/gen95_cost.py`.
- **Baseline:** the Gen90 CFD book, Sharpe 1.797.

| Test (replacement) | DEV | TEST | HOLD | Current sleeve DEV / TEST / HOLD | Book after | Verdict |
|---|---|---|---|---|---|---|
| G1 C\* on BTC/ETH only | 1.81 | 1.86 | 0.52 | 2.21 / 2.32 / 0.50 | 1.61 | rejected: the altcoins are worth their 10 bp spread |
| G2 C\* altcoins at half weight | 2.19 | 2.31 | 0.52 | 2.21 / 2.32 / 0.50 | 1.80 | rejected: no gain |
| G3 risk-sized bounce | 0.58 | 0.96 | 0.51 | 0.70 / 1.00 / 0.61 | 1.77 | rejected |

**Conclusion:** the current CFD book is already efficient on costs. No change.

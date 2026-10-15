# Gen64: own crypto ideas, round 2 (2026-10-15)

**Protocol:** `config/gen64_protocol.json`. **Script:** `scripts/gen64_crypto.py`.

| Idea | DEV | TEST | HOLD | 2023+ | 2022 | corr C* | Verdict |
|---|---|---|---|---|---|---|---|
| J1 4h trend ensemble (10/5, 20/10, 40/20), BTC/ETH/SOL | 0.87 | 1.34 | 0.46 | 0.90 | +3.9% | 0.36 | fails (HOLD, corr); no better than I6 |
| J1 same, 6 coins | 0.86 | 1.35 | 0.28 | 0.81 | +2.8% | 0.45 | fails |
| J2 12h trend 20/10 | 0.92 | 1.28 | 0.04 | 0.69 | +0.3% | 0.47 | fails |
| (reference I6, 4h 20/10) | 0.80 | 1.43 | 0.45 | 0.94 | +5.2% | 0.34 | near-miss (Gen63) |
| J3 BTC to alt lead-lag, 5-min, taker | -5.8 | -7.0 | -4.6 | -5.8 | | -0.10 | rejected |
| J3 same, maker entry | -5.0 | -5.3 | -3.4 | -4.3 | | -0.09 | rejected |

- **Multi-hour trend** consistently sits at HOLD 0.3–0.5 and correlation 0.35–0.47 with C*. It is partly the same trend exposure on a faster clock.
- **BTC to alt lead-lag** is not exploitable at 5-minute bars after costs: alts that lag BTC do not catch up within 15 minutes.

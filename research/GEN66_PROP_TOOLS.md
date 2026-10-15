# Gen66: prop risk tools for the crypto-firm portfolio (2026-10-15)

**Protocol:** `config/gen66_protocol.json`. **Script:** `scripts/gen66_prop_tools.py`.

**Setup:** portfolio C* + premium carry + cascade (equal risk, 15% vol), hourly path 2022–26, challenge 1.0x, funded 0.6x.

| Firm | Tool | Pass | Daily-loss fails | Net 2 years | Unlucky 10% | Months with income |
|---|---|---|---|---|---|---|
| HyroTrader 1-Step | baseline | 74% | 11% | $19.8k | $14.3k | 35% |
| | **S50** | 81% | 0% | **$23.6k** | **$16.7k** | 41% |
| HyroTrader 2-Step | baseline | 89% | 5% | $17.2k | $10.7k | 29% |
| | **S50** | 88% | 0% | **$20.3k** | **$12.7k** | 31% |
| CFT 1-Phase | baseline | 59% | 10% | $15.7k | $10.5k | 29% |
| | **S50** | 59% | 0% | **$20.4k** | **$15.4k** | 34% |
| SizeProp 1-Step | baseline | 54% | 27% | $18.8k | $14.7k | 38% |
| | **S50** | 69% | 6% | **$22.1k** | $14.5k (-$240) | 40% |

- **S75** (stop at 75% of the daily limit) is about neutral.
- **CUSH** (cushion scaling) is clearly worse everywhere, with or without S75.

**Verdict:**
- **S50**, a portfolio stop at 50% of the firm's daily limit (flat for the rest of the day), raises mean net and unlucky-10% net at HyroTrader 1-Step, HyroTrader 2-Step and CFT. At SizeProp the unlucky-10% net is $240 (1.6%) lower.
- So it **misses the pre-registered "all four firms" rule by a hair**. It is recommended as a per-firm setting for HyroTrader and CFT, with this deviation stated openly.
- **Caveat:** fills at the stop assume the hourly close minus 10 bp. Gap moves in crypto can fill worse, so the forward test must check real stop fills.

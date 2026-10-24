# Roll-out plan for v8.6 (2026-10-24)

All dollar figures: 2-year net per account, 2025-26 bootstrap, **planning level** (v8.6 Sharpe 1.78; Gen330 / Gen332 / Gen370). "Bad case" = p10. Fees and some terms are ASSUMED where the firm has not confirmed them.

## Gate before any purchase
1. Paper v86: at least 56 days, reconcile clean, late hours <= 5%, z > -1 (`research/PAPER_REPORT.md`).
2. Gen321 (survivorship) passed. If it fails, the book falls back to v8.4 + tranching (planning about 1.6).
3. A written OK from the firm on Netherlands access + an API bot (`research/SUPPORT_EMAILS.md`).
4. The bot has run for 1-2 weeks in dry-run next to the paper trader (`python -m qpl.bot.runner --loop`) with orders matching the paper book.

## Order of accounts

| Step | Account | Cost | Expected net 2 y | Bad case | Notes |
|---|---|---|---|---|---|
| 1 | HyroTrader 2-Step $200k **or** CFT 2-Phase $200k (whichever confirms first) | about $970 (Hyro, refunded with the first payout) / about $1,200 (CFT) | about $86-90k | about $19-25k | challenge risk 2.0, funded 1.5, daily stop 2.5%, funded cap 1.9x |
| 2 | the other of the two | as above | about $84-90k | about $19-23k | after the first payout of step 1 |
| 3 | BrightFunded 2-Step Classic $200k, swap-free (bf2.6) | about EUR 1,000 + 10% swap-free | about $69k | about $17k | MT5 EA; never without swap-free (Gen331) |
| 4 | MyFundedPerps Signature $100k | about $700 | about $35k | about $4k | risk 1.0 challenge / 2.0 funded, stop 40% of the 3% daily limit |
| 5 | Propr Classic 2-Step 3 x $100k | 3 x $749 | about $49k | about -$9k | only if the Hyperliquid check shows most of the 60 coins |

- **All five together (Gen332): about $326k over 2 years, bad case about $89k, chance of a total loss about 1.5%, fees at risk about $25-30k.**
- The accounts move together (correlation 0.7-0.8): more accounts = more money, not more safety.

## Stop rules (live)
- An account fails its challenge twice in a row -> pause new purchases, compare live with paper and the backtest.
- Live drawdown worse than -12% of the starting balance on a funded account, or 8 weeks with z < -2 vs the backtest -> stop adding accounts, review.
- Never change the strategy because of a few bad weeks; changes only as new versions after a review (`config/paper_monitor.json`).

## Not in the plan (research results)
- **The stress book** (Gen359-369) raises a combined Sharpe but earns less than a second v8.6 account in prop. Use it only for an account where v8.6 cannot run, or as a fallback, and always with its exposure cap.
- **The futures book:** needs a swing + bot futures firm, and it is worth only about $7k per $50k account. Later, as insurance.
- **Brakes and cushions** (Gen370): no gain; settings stay 2.0 / 1.5 / 2.5%.

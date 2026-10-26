# Roll-out plan (updated 2026-10-26 for v9.6)

**REVISION 2026-10-26 (Gen410 / Gen450): the cascade sleeve is survivorship-inflated. Honest v9.6 = about 3.01 backtest / planning about 1.44 (v9.6 without the cascade; the 3.20 / 1.64 below includes the inflated cascade). DECIDED: v9.7 = v9.6 without the cascade (Gen451; prepared as `paper_v97`, switch at the v96 review). Live accounts use v9.7; expectations at planning 1.44: two staggered HyroTrader accounts about $98k over 2 years, p10 +$9k, P(total loss) 6.5% (Gen452).**

**Book: v9.6** (accepted 2026-10-26, flagged; paper `paper_v96_start.bat`) = v9.5 + the Gen426 listing short (short new USDT-M perps for 30 days, 30% stop). Backtest **3.20** on the full A..Z universe (Gen436, TradFi perps excluded; 3.16 on A..S), planning Sharpe (N = 1,800) **1.64** (`results/gen436.json`). HyroTrader $200k at 1.5 / 1.5, planning level: 2025-26 $53k / p10 +$3k / P(profit) 0.92; 2022-24 $93k / +$30k / 0.99. The bot caps listing-short coins at 5% of the initial balance (HyroTrader low-cap rule) and must skip coins not listed on Bybit. The v9.5 numbers below stay as the conservative reference.

**Book: v9.5** (accepted 2026-10-25; paper `paper_v95_start.bat`): K1 sleeves (C\* point-in-time top-10, cascade, trend 4h ensemble, Weiss, deleveraging bounce, ridge ML, alt kimchi ensemble) + diversifier basket (8 BTC/ETH signals) + relative crowding (6 coins, market neutral; replicated on Bybit, Gen406). Backtest 2.98.

**Planning Sharpe (deflated, `results/plan_v95.json`): 1.41 counting all 1,770 trials of the project, 1.48 at 1,000, 1.65 at 300.**

**Sizing changed 2026-10-26 (Gen413): challenge risk 1.5 (was 2.0), funded 1.5, daily stop 2.5% (`results/plan_v95b.json`).** At planning-level Sharpe the lower challenge risk fails fewer challenges; at backtest level it costs about 3-4%.

| Per account, 2 years, 2025-26 bootstrap (challenge 1.5 / funded 1.5 / stop 2.5%) | Mean net | Bad case (p10) | P(profit) | (old 2.0 / 1.5) |
|---|---|---|---|---|
| HyroTrader 2-Step $200k, planning 1.41 | **$53k** | **+$0.1k** | **0.90** | $52k / -$5k / 0.83 |
| CFT 2-Phase $200k, planning 1.41 | $55k | -$3k | 0.86 | $54k / -$6k / 0.83 |
| MyFundedPerps $100k (**1.0 / 1.0 / 0.5 of 3%**, Gen416), planning 1.41 | $17k | -$1k | 0.87 | $11k / -$3.5k / 0.67 at 1.0 / 2.0 / 0.4 |
| HyroTrader, planning 1.65 (N = 300) | $65k | +$3k | 0.93 | $66k / -$2k / 0.89 |
| HyroTrader, weak live 1.0 | $35k | -$5k | 0.78 | $32k / -$5k / 0.69 |
| HyroTrader, backtest level | $156k | $78k | 1.00 | $162k / $76k / 0.995 |

- HyroTrader + CFT together at planning 1.41: $108k mean, P(total loss) 0.10 (was $106k / 0.16 at 2.0 / 1.5; the accounts move together).
- **Plan: start with ONE account (HyroTrader or CFT, whichever confirms bots + Netherlands first) after v96 paper GO; add the second only once live results support Sharpe >= 1.4, and at least 3-6 months after the first (Gen437: same mean, P(total loss) 0.10 -> 0.06 with a 180-day gap); MyFundedPerps at 1.0 / 1.0 / 50% stop is now a reasonable third account (P(profit) 0.87, Gen416).**
- BrightFunded (MT5 CFDs) needs its own honest version of the book (bf2.6 had the withdrawn carry sleeves); not in the plan until that exists.

## Release policy: research vs paper trading (agreed 2026-10-26)
- **One paper book runs: v96** (started 2026-10-26). Its code is frozen for at least 56 days (gate in `config/paper_v96.json`; extend to 112 days if -2 <= z <= -1).
- Research continues; accepted improvements are collected in ONE candidate (v9.7) and do **not** touch the running paper. A switch happens only at a review (after the gate), or earlier only for a large gain (planning Sharpe +0.15 or more).
- **Out-of-sample tracking without a new paper run:** every test is registered (dated protocol) before it is run; after the registration date its P&L on new data is genuinely out of sample. Candidate sleeves are recomputed over the live period with the paper code's own point-in-time machinery (self-test standard) and shown next to the v96 paper ledger.
- At a switch, sleeves that stay keep their live record (the paper ledger is per sleeve); only new sleeves start from zero. A new paper run is needed only for new live data feeds.

---

## Earlier version (2026-10-24 / 25), kept for the record

# Roll-out plan (2026-10-24, updated 2026-10-25 after Gen321-374)

**Update 2026-10-25:** the survivorship tests (Gen321 / 326 / 372-374) withdrew the wide carry and the stress book. The live candidate is now **K1 / v9.0** (C\* on a monthly point-in-time top-10, cascade, trend 4h, Weiss, deleveraging bounce, ridge ML, alt kimchi; no carry): backtest 2.39, **planning Sharpe about 0.85-1.1** (Gen377, the deflated-Sharpe method used for the old 1.78; the 1.37 from Gen373 was too optimistic). At planning level 0.84 one HyroTrader / CFT $200k account is about **$25-27k over 2 years, bad case about -$5k, P(profit) about 0.70-0.74**; all four planned accounts about $85k, P(total loss) 0.21 (Gen377). **Start with ONE account; add more only after paper / live results support a Sharpe of 1.5+.** Dollar figures in the table below are the OLD v8.6 numbers; scale them by about 0.8 (net) and expect much smaller bad cases.

All dollar figures: 2-year net per account, 2025-26 bootstrap, **planning level** (v8.6 Sharpe 1.78; Gen330 / Gen332 / Gen370). "Bad case" = p10. Fees and some terms are ASSUMED where the firm has not confirmed them.

## Gate before any purchase
1. Paper v86: at least 56 days, reconcile clean, late hours <= 5%, z > -1 (`research/PAPER_REPORT.md`).
2. Gen321 (survivorship): FAILED (2026-10-25). The book is K1 / v9.0 (Gen373); it needs its own paper record (the K1 shadow on the v86 ledger plus a point-in-time C* paper sleeve).
3. A written OK from the firm on Netherlands access + an API bot (`research/SUPPORT_EMAILS.md`).
4. The bot has run for 1-2 weeks in dry-run next to the paper trader (`python -m qpl.bot.runner --loop`) with orders matching the paper book.

## Order of accounts

| Step | Account | Cost | Expected net 2 y | Bad case | Notes |
|---|---|---|---|---|---|
| 1 | HyroTrader 2-Step $200k **or** CFT 2-Phase $200k (whichever confirms first) | about $970 (Hyro, refunded with the first payout) / about $1,200 (CFT) | about $86-90k | about $19-25k | challenge risk 2.0, funded 1.5, daily stop 2.5%, funded cap 1.9x |
| 2 | the other of the two | as above | about $84-90k | about $19-23k | after the first payout of step 1 |
| 3 | BrightFunded 2-Step Classic $200k, swap-free (bf2.6) | about EUR 1,000 + 10% swap-free | about $69k | about $17k | MT5 EA; never without swap-free (Gen331) |
| 4 | MyFundedPerps Signature $100k | about $700 | about $35k | about $4k | risk 1.0 challenge / 1.0 funded, stop 50% of the 3% daily limit (Gen416; was 1.0 / 2.0 / 40%) |
| 5 | Propr Classic 2-Step 3 x $100k | 3 x $749 | about $49k | about -$9k | only if the Hyperliquid check shows most of the 60 coins |

- **All five together (Gen332): about $326k over 2 years, bad case about $89k, chance of a total loss about 1.5%, fees at risk about $25-30k.**
- The accounts move together (correlation 0.7-0.8): more accounts = more money, not more safety.

## Stop rules (live)
- An account fails its challenge twice in a row -> pause new purchases, compare live with paper and the backtest.
- Live drawdown worse than -12% of the starting balance on a funded account, or 8 weeks with z < -2 vs the backtest -> stop adding accounts, review.
- Never change the strategy because of a few bad weeks; changes only as new versions after a review (`config/paper_monitor.json`).

## Not in the plan (research results)
- **The stress book** (Gen359-369): FAILED the point-in-time test (Gen374: expected live 0.39). Dropped.
- **The futures book:** needs a swing + bot futures firm, and it is worth only about $7k per $50k account. Later, as insurance.
- **Brakes and cushions** (Gen370): no gain; settings stay 2.0 / 1.5 / 2.5%.

# CFD firm comparison for the crypto CFD book: FundedNext, FTMO, BrightFunded (2026-10-18)

**Method:**
- Starting point: the user's own findings.
- Official sites could not be fetched from the research container: fundednext.com, ftmo.com, help.brightfunded.com and ftmo.oanda.com all fail DNS.
- Every fact below therefore comes from search-engine summaries of official help-centre pages, or from third-party sites. Each fact is labelled.
- **Scripts:** `scripts/gen100_firm_costs.py` and `scripts/gen100_firm_caps.py` re-price the frozen signals (point-in-time verified in Gen96) under each firm's conditions.
- **Results:** `results/gen100_firms.csv` and `results/gen100_caps.csv`.

**Labels:**
- **[O]** = official page, as summarised by the search engine;
- **[3P]** = third-party site;
- **[?]** = not found / unverified.

## 1. Facts and contradictions

| Item | FundedNext | FTMO | BrightFunded |
|---|---|---|---|
| Swap-free available | **Yes**, all challenges, +10% price, same spreads, leverage and rules [O help centre]; must be bought with the challenge, cannot be added later [3P] | **No swap-free account** [3P Propvator]; nothing official found | **Contradictory:** "Swap-Free Add-On at purchase" [3P Propvator page 2, GodFunded "+10%"] vs "does not offer swap-free" [3P Propvator page 1] |
| Swap-free covers crypto | Help-centre example uses BTCUSD [O]; no explicit statement for all symbols [?] | n/a | [?] |
| Crypto commission | **0.04% of notional per side** (example: 1 lot ETH at 2,722 = $1.08) [O help centre] | **0.0325% per side** [3P]; your FTMO source says the same | **0.012% per side (0.024% round turn)** [3P PropFirmMatch]; [O] page not reachable |
| Crypto symbols | **BTC, ETH, XRP, ADA, DOGE, LINK, LTC, XLM, XMR** [O instruments article] -> **no SOL, AVAX, DOT, BCH** | BTC ETH SOL XRP ADA DOGE DOT AVAX LTC per your FTMO blog source; LINK and BCH [?] | 35-40 pairs; SOL DOT AVAX ADA LINK XRP [3P]; BCH added [O news via GodFunded]; **LTC and DOGE [?]** |
| Crypto leverage | **Contradictory:** BTC/ETH/SOL 1:5, others 1:2 [3P GodFunded] vs 1:1 (our old preset) | 1:3.3 Standard, **1:1 Swing** [O FTMO article, about 4 years old; 3P LuxAlgo] | 1:5 [3P] |
| BTC/ETH spread | [?] not published | [?] variable; FTMO says read it in the platform [O trading update] | [?] variable [3P] |
| Swap rates (standard accounts) | [?]; swaps count toward the daily loss limit; crypto triple swap on Friday [3P] | [?] per instrument in the platform; triple swap Wednesday [3P] | [?] per instrument in the platform [3P] |
| Weekend holding | Stellar 1-Step, 2-Step and Lite: **reinstated 2026-05-08** after a suspension from 2026-01-17 [3P GodFunded]; older guide says no weekend holding on the funded account [3P Propvator] -> **contradictory for funded** | Evaluation: allowed. **Funded Standard: must close before the weekend.** Swing: allowed [3P x3, FTMO FAQ via search] | Allowed in all phases [3P x3] |
| EAs / automated trading | **[?]** Only the FundedNext *Futures* page says EAs are allowed [3P] | Allowed on all accounts if within the rules [3P x2] | **Contradictory:** allowed [LuxAlgo, Trusted Prop, Lune "with manual oversight"] vs "EAs not allowed" [GodFunded] |

**Swap rates elsewhere, as a sanity check for our 3.3 bp/day (about 12%/yr) assumption. These are other brokers, NOT these firms:**
- Afterprime BTCUSD long: -26 USD per lot per night. That is about 2.4 bp/day at BTC around $110k, about 9%/yr.
- OANDA TMS crypto: -33.6%/yr long, -26.4%/yr short.

So real crypto CFD swaps plausibly run 9-34%/yr. Our 12% sits at the low end; at 24%/yr the standard-account book drops by about 0.1 Sharpe (Gen96 cost stress).

## 2. Two issues that the earlier "1.80 / 2.07" figures did not capture

1. **Coin universe.** C\* trades BTC ETH XRP ADA SOL DOGE AVAX DOT LINK, and trend 4h trades BTC ETH SOL.
   - At FundedNext, SOL, AVAX and DOT are not on the published list.
   - C\* loses 3 of its 9 coins and trend 4h loses SOL.
2. **Leverage caps.** At the challenge size (1.5x, book at 15% vol) the book's gross exposure is:
   - median 0.05x, 99th percentile 1.0-1.5x;
   - maximum **7-8x of equity**, which is the Weiss trade: a rare 2-hour trade that the risk weighting sizes up.
   - With a 1:1 crypto cap the book is over the cap in 1-4% of hours, and those hours are its best ones.

## 3. The book re-priced (2022-26, frozen signals; 'base' spreads 5 / 10 bp, 'low' 2 / 5 bp, plus each firm's commission)

| Case | Sharpe | 2023-24 | 2025-26 | Return a year at challenge size |
|---|---|---|---|---|
| Model used so far: 3-sleeve CFD book, 5/10 bp all-in, swap 3.3, no cap | 1.80 | 3.08 | 1.32 | 40% |
| Model used so far: 5-sleeve swap-free book, no cap | 2.10 | 3.42 | 1.42 | 47% |
| **FundedNext swap-free, 5-sleeve, 6 coins, +4 bp, cap 1:1** | **1.46** (low spread 1.64) | 2.49 | 0.84 | 31% |
| FundedNext swap-free, 5-sleeve, 6 coins, +4 bp, cap 1:5 (if the 1:5 claim is right) | 1.74 | 2.81 | 1.08 | 39% |
| FundedNext standard, 3-sleeve, 6 coins, +4 bp, swap 3.3, no cap | 1.61 | 2.79 | 1.12 | |
| **FTMO evaluation, 3-sleeve, +3.25 bp, swap 3.3, cap 1:3.3** | **1.59** | 2.77 | 1.16 | 35% |
| FTMO funded Swing (weekend allowed), cap 1:1 | 1.40 | 2.51 | 1.05 | 28% |
| **FTMO funded Standard (flat every weekend)** | **0.81** | 1.73 | 0.82 | |
| BrightFunded standard, 3-sleeve, no LTC/DOGE, +1.2 bp, swap 3.3, cap 1:5 | 1.65 | 2.96 | 1.27 | 37% |
| **BrightFunded swap-free (if the add-on exists), 5-sleeve, +1.2 bp, cap 1:5** | **1.97** (low spread 2.15) | 2.99 | 1.51 | 44% |

All figures are backtests. After the Gen96 discount for trial count, expect roughly 0.3-0.5 lower live.

## 4. Conclusions

1. **"Swap-free gives 2.07" does not hold at FundedNext.**
   - Its coin list lacks SOL, AVAX and DOT, its commission is the highest (4 bp per side), and its crypto leverage may be 1:1.
   - Realistic: **1.46-1.74**, depending on leverage and spreads. That is about the same as the standard-swap books elsewhere.
2. **FTMO is a poor fit for the funded stage.**
   - A Standard funded account must be flat at weekends, which halves the Sharpe (0.81).
   - The Swing account allows weekends, but its crypto leverage is 1:1 (1.40).
   - The evaluation itself is fine (1.59).
3. **BrightFunded is the best fit on paper:** lowest commission (1.2 bp), widest coin list, 1:5 leverage, weekend holding allowed.
   - Standard swap: 1.65. With the swap-free add-on: 1.97-2.15.
   - **But three facts are unverified:**
     - whether the swap-free add-on exists, and its price;
     - LTC/DOGE availability;
     - whether EAs are allowed (the sources contradict each other).
4. **The single most valuable unknown is crypto leverage per firm.** A 1:1 cap costs 0.25-0.4 Sharpe because it clips the Weiss trade.
   - A code-level fix is possible: cap Weiss at the firm's limit. That is a pre-registered rule change for a later generation, not done here.

## 5. What can only be settled inside the platform or by support (not online)

For each firm, from the MT5 / cTrader symbol specification, or support in writing:
- **Crypto leverage:** BTCUSD and ETHUSD max leverage, and altcoin leverage.
- **Costs:** typical spread on BTCUSD and ETHUSD, and long / short swap.
- **Symbol list:** which of SOL, AVAX, DOT, LINK, BCH, LTC, DOGE exist on the account type.
- **BrightFunded:** does the swap-free add-on exist, what does it cost, and does it cover crypto?
- **Automation:** are EAs / automated execution allowed on the funded account? This is especially open at BrightFunded and FundedNext.
- **FundedNext:** is weekend holding allowed on the funded account (not only the challenge) as of now?

A free trial or demo account in each firm's platform answers the first three without contacting anyone.

## Sources (as returned by search; official pages could not be opened directly)

**FundedNext:**
- [swap-free accounts (help centre)](https://help.fundednext.com/en/articles/8019806-does-fundednext-offer-swap-free-accounts)
- [commissions (help centre)](https://help.fundednext.com/en/articles/10701368-what-are-the-commission-charges-for-stellar-challenges-and-fundednext-accounts)
- [instruments (help centre)](https://help.fundednext.com/en/articles/8224087-what-instruments-are-allowed-to-be-traded-at-fundednext)
- [Propvator FundedNext instruments](https://propvator.com/blog/fundednext-instruments/)
- [GodFunded FundedNext](https://thegodfunded.com/en/firms/fundednext)
- [GodFunded: weekend holding reinstated](https://thegodfunded.com/en/news/fundednext-reinstates-weekend-holding-for-trading-accounts)
- [Propvator weekend rule](https://propvator.com/blog/fundednext-weekend-holding-rule/)
- [FundedTrading swap-free list](https://fundedtrading.com/best-swap-free-prop-firms/)

**FTMO:**
- [Propvator FTMO trading conditions](https://propvator.com/blog/ftmo-trading-conditions/)
- [FTMO trading update 15 Oct 2026](https://ftmo.oanda.com/blog/trading-updates/trading-update-15-oct-2026/)
- [FTMO FAQ: overnight / weekend](https://ftmo.oanda.com/faq/do-i-have-to-close-my-positions-overnight-or-before-weekend)
- [FTMO article: leverage](https://ftmo.com/en/a-few-answers-to-your-questions/)
- [LuxAlgo FTMO](https://www.luxalgo.com/prop-firms/ftmo/)
- [TradingFunder weekend rules](https://tradingfunder.com/concepts/weekend-holding-rules/)
- [FTMO crypto instruments blog](https://ftmo.com/en/blog/ftmo-enhances-crypto-trading-new-instruments-and-better-spreads/)

**BrightFunded:**
- [PropFirmMatch BrightFunded](https://propfirmmatch.com/prop-firms/brightfunded)
- [Propvator BrightFunded conditions](https://propvator.com/blog/brightfunded-trading-conditions/)
- [Propvator weekend rule](https://propvator.com/blog/brightfunded-weekend-holding-rule/)
- [GodFunded BrightFunded](https://thegodfunded.com/en/firms/brightfunded)
- [BrightFunded: 16 new crypto pairs](https://thegodfunded.com/en/news/brightfunded-expands-crypto-offering-with-16-new-trading-pairs)
- [LuxAlgo BrightFunded](https://www.luxalgo.com/prop-firms/brightfunded/)

**Swap comparisons (other brokers):**
- [Afterprime BTCUSD swap](https://afterprime.com/swaps/btcusd)
- [OANDA TMS swap points](https://www.oanda.com/eu-en/document/91)

## Update 2026-10-19: FundedNext text received by the user (help centre / support)

**Now confirmed by FundedNext's own text:**
- **Crypto commission:** lot x contract size x open price x **0.04% per trade side**, already modelled at 4 bp per side. It applies to all models, including Stellar and FundedNext Accounts.
- **Swap-free:** available on **all challenges**, at a price **10% higher**. "Swap charges do not apply to Swap-Free Accounts."
- **Overnight and weekend holding:** overnight is allowed on Stellar 1-Step, 2-Step and Lite. **Weekend holding is allowed on Challenge accounts AND FundedNext (funded) accounts.** This resolves the earlier contradiction in favour of holding.
- **Swaps on standard accounts:** shown in MT5 under Specification; they count toward the daily-loss calculation. Crypto triple swap is Friday on MT4 / MT5 / cTrader, Wednesday on Match-Trader.

**Still open for FundedNext. This is the only thing that moves the estimate between 1.46 and about 1.85:**
1. Crypto symbol list: are SOL, AVAX, DOT available? The help-centre list says no.
2. Crypto leverage on BTC/ETH and on altcoins: 1:1, 1:2 or 1:5?
3. Typical BTCUSD / ETHUSD spread.
4. Explicit confirmation that swap-free covers crypto CFDs, not only FX.
5. Expert advisors / automated execution allowed on Stellar challenge and funded accounts.

**Effect on the estimate:**
- The book cost model already used the confirmed 4 bp commission and swap 0.
- Weekend holding being allowed on the funded account removes a downside risk that was not yet priced in.
- The range stays **1.46 (1:1, 6 coins, 5/10 bp spreads) to 1.74 (1:5)**. The upper end rises to about 1.85 if SOL, AVAX and DOT turn out to be available. These are backtests; expect less live (Gen96).

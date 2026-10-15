# Crypto perpetual-futures positioning strategies (funding, OI, long/short, liquidations, basis/premium)

Scope note: research done 2026-10-15. WebFetch and curl to arxiv.org, ssrn.com, bis.org, sciencedirect.com, researchgate.net and aeaweb.org were blocked (DNS/proxy 403) in this environment, so most evidence comes from search-engine abstracts and summaries, plus one GitHub audit that could be fetched in full. Exact table values (Sharpe by cost tier, thresholds) from the core papers could NOT be read and are listed as gaps. Nothing below is invented; where a rule is my own proposed test spec, it is under "Inferences".

Project exclusions respected: Wen et al. 2022 hour pairs, Chi et al. 2023 basis factor (5d, daily rebalance), Inan 2025 funding-forecast contrarian, BTC funding contrarian at 90/95th pct with 24-72h hold, BTC/ETH funding carry (~3%/yr). They come up below only where new evidence bears on them.

---

## Q1. Which funding-rate, open-interest and long/short-ratio signals predict returns out of sample, at what horizons, and do they survive taker (~5 bp/side) or need maker (~2 bp) costs?

### Takeaway
Out-of-sample evidence that funding, OI or long/short ratios predict *directional* returns is thin, and much of it is negative. The best-documented cross-sectional result is that the perp **log-basis** (equivalently, funding/premium) is one of two factors pricing perp returns (Cao et al., JFM 2024). That overlaps heavily with the already-rejected Chi et al. basis factor. Independent audits and a 2026 SSRN post-mortem find that the cross-sectional funding "crowding" signal disappears point-in-time and loses money net of costs at 8h-7d horizons. I found **no academic study at all** testing Binance top-trader or all-account long/short ratios as return predictors.

### Cited Findings
**Cross-sectional basis/funding as a priced factor**
- Cao, Luo, Cheng & Dong, "Anatomy of Cryptocurrency Perpetual Futures Returns" (SSRN 6365329). They build a cost-of-carry model for perps and test 170 predictors (basis, momentum, liquidity, size, volatility). 63 sorts give significant *total* returns (price plus funding). A two-factor model (log-basis plus a price-volume factor) explains all 63. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6365329)
- The published version (Journal of Futures Markets, 2024; Cao, Zhai, Luo) reports 134 predictors and 48 significant strategies, all explained by basis plus price-volume factors. Cite the JFM version for final numbers. — [Edinburgh Research Explorer](https://www.research.ed.ac.uk/en/publications/anatomy-of-cryptocurrency-perpetual-futures-returns/); [Luo PhD thesis](https://era.ed.ac.uk/items/ed3909ca-1fc6-4e44-9c49-89c9ed77f5b9)

**Negative / failed replications (cross-sectional funding)**
- Fayez Junior, "Failure of Cross-Sectional Alpha Screening on Cryptocurrency Perpetual Futures: A Quantitative Post-Mortem Using OHLCV and Funding Rate Signals" (SSRN 6701738). Long-short portfolios on Binance perps. The evidence "compels rejection" of exploitable cross-sectional alpha from OHLCV and funding signals at an **8-hour horizon**. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6701738)
- mtrinkner/crypto-funding: a pre-registered, hash-chained practitioner audit with all trials reported. Trial 22 is "funding as crowding signal": cross-sectional 7-day, short high-funding / long low-funding.
  - In-sample: IC +0.06 (t 2.15), but the price leg was wrong-signed and the net book lost **78.9%/yr**.
  - Point-in-time universe: IC +0.0001 (t 0.00).
  - Cross-sectional 30d variant: net -64.0%/yr. Time-series 7d / 30d variants: -14.1% / -19.8%.
  — [GitHub mtrinkner/crypto-funding](https://github.com/mtrinkner/crypto-funding)
- The same audit, trial 27: cross-sectional price momentum on the top 20, 21-day, gave 30.4% net with Sharpe 0.52. The 7-day version gave -0.03, and 1-day reversal gave **-1.41** after costs. — [GitHub mtrinkner/crypto-funding](https://github.com/mtrinkner/crypto-funding)
- Kim & Lim, "From Predictability to Tradability: Machine-Learning Signals and Trading Frictions in Cryptocurrency Markets" (SSRN 7115197). Cross-sectional ML signals are weak but detectable and often do not survive transaction costs and frictions. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7115197)

**Practitioner claims (unverified, vendor)**
- Presto Labs (practitioner research): funding-rate changes explain about 12.5% of the variation in 7-day price changes for a single asset. Funding "may be more useful cross-sectionally", but the alpha needs turnover reduction. — [Presto Labs](https://www.prestolabs.io/research/can-funding-rate-predict-price-change) (summary via search; page not fetchable)
- Aperiodic blog: a "soft carry" factor shorts the highest-funding coins and buys the lowest, unhedged, using an OI-weighted composite funding rate across exchanges. It is part of three orthogonal portfolios claimed at Sharpe about 2.5. This is a vendor claim with no audit trail. — [Aperiodic](https://blog.aperiodic.io/p/cross-sectional-alpha-factors-in)

**Time-series (BTC) predictability using positioning variables**
- Palazzi, Junior & Klotzle (SSRN 6725492): crypto-native positioning variables, including **open interest and funding rates**, predict Bitcoin returns across regimes. Macro-financial variables gain power only after 2019. Horizon and OOS R² could not be read. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6725492)
- Zhang, Ma, Arkorful & Peng (Finance Research Letters 2023): unexpected futures OI relates *negatively* to BTC volatility over the long run, and unexpected volume relates positively. This is a volatility result, not a return result. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/finana/v86y2023ics1057521923000133.html)
- An open-interest "speculation index" (volume/OI) and leverage estimated from liquidations are used for market-structure analysis, not return forecasting. — [arXiv 2102.04591](https://arxiv.org/pdf/2102.04591)

**Order flow / taker imbalance (uses your taker-buy volume data)**
- Kim & Hansen, "The Quarter-Hour Effect" (arXiv 2607.09426, July 2026).
  - Sample: Binance perps BTC, ETH, XRP, SOL, DOGE and ADA, 2021-01 to 2024-10.
  - Quarter-hour opening returns are predictable out of sample.
  - **Opening order imbalance predicts returns over 4-12 hours.**
  - Secondary coverage says the per-trade edge (about 0.51 bp gross; OOS R² 3.4%) is **too small to cover fees**. That attribution to this paper is not certain.
  — [arXiv](https://arxiv.org/pdf/2607.09426); [CryptoSlate](https://cryptoslate.com/the-invisible-opening-bell-inside-cryptos-endless-trading-day/)
- "Order Flow and Cryptocurrency Returns" (Journal of Financial Markets 2026, S1386418126000029) applies the Evans-Lyons framework. World order flow explains about 11% of daily crypto returns, and one model's long-short Sharpe is 3.61. Authors and cost treatment could not be verified. — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1386418126000029); [tradingstrategy.ai summary](https://tradingstrategy.ai/docs/learn/order-flow.html)

**Long/short ratios**
- No peer-reviewed or working paper tests Binance/Bybit/OKX account or top-trader long/short ratios as predictors. Media pieces assert "70%+ one side = contrarian" with no backtest. — [cryptorank](https://cryptorank.io/news/feed/4f469-bitcoin-perpetual-futures-long-short-ratios-binance-okx-bybit); [Bitsgap](https://bitsgap.com/blog/bitcoin-open-interest-explained)

**Mechanics relevant to signal design**
- OI does not enter the Binance funding formula. Funding is roughly the time-average premium (perp vs index) over the prior 8h, with a clamp around the interest component. The Binance parameters in He et al. are κ=1, γ=0.05% and ι=0.01%. — [Coincub](https://coincub.com/blog/perpetual-futures-funding-rates-78-of-a-quarter-at-0-01/); [He et al. arXiv](https://arxiv.org/pdf/2212.06888)
- Funding sits at the 0.01% floor most of the time: "78% of a quarter at 0.01%" per one practitioner tally. Funding *levels* are therefore a censored, low-information signal; premium-index deviations carry more variation. — [Coincub](https://coincub.com/blog/perpetual-futures-funding-rates-78-of-a-quarter-at-0-01/)

### Inferences
- Cross-sectional funding/basis is the one positioning variable with published factor-level support (Cao et al.). Practically, it is the same object as the rejected Chi et al. basis factor. Two independent tests (SSRN 6701738; mtrinkner trial 22) show it fails net of costs at 8h-7d rebalancing. A retest only makes sense with materially different design: weekly or monthly rebalancing, a premium-index z-score rather than raw funding, and a beta-neutral, *funding-collecting* framing.
- The positive directional evidence for OI/funding (Palazzi et al.) is BTC-only, regime-dependent, and the OOS details were not verifiable. Treat it as a hypothesis, not evidence.
- Long/short ratios have **zero** academic support. They are worth testing only as a cheap pre-registered exploratory family, with tight multiple-testing control. Suggested spec: z-score of the 7-day change in the top-trader position ratio minus the all-account ratio ("smart minus retail"), cross-sectional rank, weekly rebalance.
- Taker-imbalance edges at 15-min to 12h horizons appear to be about 0.5-1.3 bp gross per trade (also see Q4). That is below 5 bp/side taker and even below 2 bp maker, so intraday order-flow signals are effectively untradable for this project unless aggregated into slower (daily or longer) signals.
- **Maker vs taker:** every directional signal here with a horizon of 1 day or less is cost-dominated. Weekly-or-slower cross-sectional books are the only ones whose turnover could plausibly fit within about 10 bp round-trip taker costs.

### Gaps
- Exact OOS R², horizons and Sharpe for Palazzi et al., Cao et al. (factor premia net of costs), and the JFM "Order flow" paper could not be read because the full text was blocked.
- No study found that tests OI change (5-min data) as a time-series or cross-sectional predictor with costs.
- No study found on top-trader vs all-account long/short ratios.

---

## Q2. What does research say about liquidation cascades (detection from price/volume/OI drops) and subsequent reversal or continuation? Exact rules and horizons?

### Takeaway
Liquidation cascades are well studied as *events* (mechanics, early warning, October 10-11 2025), but I found **no peer-reviewed event study with a tradable post-cascade reversal rule and net returns**. The best indirect evidence is Gornall-Rinaldi-Xiao: perp drawdowns are about one-third the size of quarterly-futures drawdowns and **mean-revert quickly**. "Buy after the cascade" is described in practitioner notes as folklore whose reversal is still an open empirical question.

### Cited Findings
- Gornall, Rinaldi & Xiao, "Perpetual Futures and Basis Risk: Evidence from Cryptocurrency" (SSRN 5036933, Jan 2025; AEA 2026 program; earlier titled "Funding Payments Crisis-Proofed Bitcoin's Perpetual Futures").
  - Data: hourly BTC from BitMEX.
  - Despite being forced sales, liquidations have *limited* price impact.
  - **Perp drawdowns quickly mean-revert, while quarterly-futures drawdowns persist**, and perp drawdowns are about 1/3 the size.
  - Funding payments stay small even in crises.
  — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5036933); [AEA](https://www.aeaweb.org/conference/2026/program/paper/ByyFEfr4); [ResearchGate earlier version](https://www.researchgate.net/publication/388019725_Funding_Payments_Crisis-Proofed_Bitcoin's_Perpetual_Futures)
- BitMEX perps: daily forced liquidations relative to outstanding futures average **3.51%** (1.89% long, and the rest short per the snippet). Leverage is estimated from liquidations. — [arXiv 2102.04591 / Applied Economics 2021](https://arxiv.org/html/2102.04591v1)
- arXiv 2607.27070, "Where does the criticality live?":
  - Studies 7 BTC perp liquidation cascades (2022-2025, including October 2025).
  - Uses minute prices plus 5-min leverage and order-flow data.
  - Finds early-warning signals are **event-heterogeneous**: no single precursor works across cascades.
  - Notes that Binance per-event liquidation snapshots are no longer served, so intraday liquidation data needs a commercial source.
  — [arXiv](https://arxiv.org/pdf/2607.27070)
- arXiv 2608.03616 models cascade dynamics as "subcritical branching inside a first-order transition" (mechanism paper, no trading rule found). — [arXiv](https://arxiv.org/pdf/2608.03616)
- Lim, "Anatomy of a Crypto Cascade: Minute-Level Evidence from the October 2025 Crash" (SSRN 6579278): minute-level Binance/Bybit data, futures led the crash. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6579278). Ali (SSRN 5611392) uses GARCH/event-study methods on the same event and finds volatility persistence and contagion. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5611392). Neither abstract reports post-event return reversals.
- "Delayed Marks, Funding Memory, and Forecasting Liquidation-Tail Risk in Crypto Perpetual Futures" (MDPI Forecasting 8(5):76) forecasts liquidation-tail *risk* from mark-price delays and funding persistence. — [MDPI](https://www.mdpi.com/2571-9394/8/5/76)
- The Open-Alpha-Lab study notes (#586 liquidation cascade) treat post-cascade buying as practitioner folklore and an open question. They cite Brunnermeier-Pedersen (2009) for spiral mechanics and Nagel (2012) for reversal returns rising in liquidity stress. — [GitHub Open-Alpha-Lab](https://github.com/Guillain-RDCDE/Open-Alpha-Lab/blob/main/studies/586-liquidation-cascade/docs/references.md) (summary via search; fetch returned 503)
- Kaiko: the February (2025) liquidation waves cut top-10 altcoin leverage, framed as potentially supporting a steadier uptrend. This is descriptive, with no return statistics. — [ChainCatcher citing Kaiko](https://www.chaincatcher.com/en/article/2170720)
- Liquidations can trigger on temporary price moves (mark price/engine design), per an SEC comment letter from researchers. — [SEC](https://www.sec.gov/comments/S7-2026-21/s7202621-1011079-3235289.pdf)

### Inferences
- Proposed testable cascade-reversal rule, inferred from the mechanism and not from a paper. All thresholds are pre-registered and should be swept on 2020-2022 only, then frozen.
  - **Long-cascade detection:** 1h return below -k·σ(1h, 30d), with k in {3,4}; 5-min OI drop over the same hour below -q percent; and 1h volume above its 95th percentile.
  - The OI drop is a proxy for forced closes, since Binance historical liquidation prints are unavailable.
  - Optional filter: taker-sell share above 60%.
  - **Entry:** long at the first 5-min bar after the hour closes. Mirror for short squeezes.
  - **Hold:** 4h / 12h / 24h. **Stop:** cascade low minus 1 ATR.
  - **Universe:** your 20 coins; also test BTC-only. A cross-sectional variant buys the coins with the largest OI flush on market-wide cascade days.
- Gornall et al. imply the reversal lives mostly in perp-vs-spot dislocation (basis) and in drawdown depth. Measuring the reversal on the premium index, not just on price, is the cleaner test.
- Events are rare (dozens per coin over 2020-2026) and clustered (all coins cascade together). Effective sample size is small, so this is likely to be an overlay or "crisis alpha" sleeve, not a standalone strategy.
- Correlation with long-only trend: a cascade-reversal *long* buys exactly when trend followers are being stopped or cut. It should be low or negative-correlated in timing, but it adds long beta in crash regimes.

### Gaps
- No primary source with post-cascade net returns, hit rates or horizons was found.
- Gornall et al.'s reversal horizon (hours vs days) could not be read.
- Binance historical liquidation-order data availability for 2020-2026 is unresolved; the cascade paper says snapshots are no longer served.

---

## Q3. Cross-sectional funding/basis carry in perps (long low funding, short high funding): reported returns and decay after 2022?

### Takeaway
Delta-neutral cash-and-carry (short perp, long spot) earned very high Sharpe in 2020-2023, but the carry Sharpe fell to about 4 from 2024 and **turned negative in 2025**. Independent audits put out-of-sample, liquidation-adjusted carry Sharpe near 1 or below and decaying toward zero by 2025-26. The cross-sectional unhedged "long low funding / short high funding" version has no peer-reviewed net-of-cost support, and audits show it loses money.

### Cited Findings
- Christin, Routledge, Soska & Zetlin-Jones, "The Crypto Carry Trade" (2022 WP; Management Science 2024, doi 10.1287/mnsc.2024.05069). Short futures hedged with spot on one large exchange has **in-sample Sharpe 7-10**. Demand for long levered exposure makes the long side expensive. — [CMU WP PDF](https://www.andrew.cmu.edu/user/azj/files/CarryTrade.v1.0.pdf); [Management Science](https://pubsonline.informs.org/doi/references/10.1287/mnsc.2024.05069)
- Schmeling, Schrimpf & Todorov, "Crypto Carry" (BIS WP 1087, 2023; CEPR DP 20719, 2025).
  - Carry (futures minus spot) reaches up to about 60% p.a. (RePEc summary says "sometimes >40%") and varies strongly over time.
  - It is driven by trend-chasing small investors seeking leverage and by scarce arbitrage capital.
  - High carry coincides with margin spikes and liquidations in drawdowns, and is linked to crash risk.
  — [BIS](https://www.bis.org/publ/work1087.htm); [CEPR](https://cepr.org/publications/dp20719)
- Borri, Liu, Tsyvinski & Wu, "Cryptocurrency as an Investable Asset Class: Coming of Age" (arXiv 2510.14435, Oct 2025). Crypto carry, mostly driven by funding, has **Sharpe 6.45 over 2020-2025**, falling to **4.06 from 2024** and **negative in 2025**. Compressed funding premia threaten yield products like Ethena. — [arXiv](https://arxiv.org/pdf/2510.14435)
- "Exploring risk and return profiles of funding rate arbitrage on CEX and DEX" (Blockchain: Research and Applications, 2025; Binance, BitMEX, ApolloX, Drift).
  - Price convergence supplied about 63% (BTC) and 65% (ETH) of the return.
  - BTC Sharpe is 3.53 at zero fees and **1.80 under high retail trading costs**.
  — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2096720925000818)
- mtrinkner/crypto-funding audit, pre-registered:
  - Always-on carry over 16 coins: 4.0% excess, Sharpe 0.87. The point-in-time universe of 109 coins: 3.0%, 0.51. BitMEX 2017-23: -0.15.
  - Switching carry on when trailing 30d funding is positive (weekly, 3x): Sharpe 1.71 (16 coins) and 1.92 (point-in-time). The 94-coin holdout gives 1.70 *before* liquidations, but **1.02 / -0.24 / -1.81 with 2% / 5% / 10% liquidation penalties**.
  - The risk-engineered primary version (inverse-vol 2x, holdout, 5% liquidation penalty) gives 1.24, **decaying to 0.13 in 2025-26**.
  - Verdict: nothing clears an OOS Sharpe of 1.5.
  — [GitHub](https://github.com/mtrinkner/crypto-funding)
- Lei Lu (Manitoba), "The Risk and Return of Cryptocurrency Carry Trade" (presented December 2024). Cross-sectional carry *long high-interest / short low-interest* cryptos earns **43.4% p.a., Sharpe 0.74**. It is not explained by crypto factors and is partly an equity-volatility risk premium. It is unclear whether "interest" means perp funding or lending rates. — [ZUEL event page](https://dtf.zuel.edu.cn/szjsyxdjr-szjs_tzyg/szjsyxdjr_cont_news/details-40034.html)
- Funding spreads across exchange types are very persistent, with potentially permanent volatility shocks ("Two-Tiered Structure of Cryptocurrency Funding Rate Markets", MDPI Mathematics 14(2):346). — [MDPI](https://www.mdpi.com/2227-7390/14/2/346)
- Cross-venue funding dispersion (Hyperliquid vs dYdX, 2x, 30d) gives Sharpe 0.39 net, and -0.36 in 2025-26, against **3.69 gross**: costs eat it. — [GitHub mtrinkner](https://github.com/mtrinkner/crypto-funding)

### Inferences
- Decay after 2022 is consistent across three independent sources: the Borri et al. Sharpe path, the mtrinkner holdout decay, and the project's own about 3%/yr BTC/ETH result.
- The 20-coin cross-sectional delta-neutral version (long spot / short perp on high-funding alts) is the most promising remaining variant. Sources show alts carry more funding but also more liquidation and tail risk. Liquidation-penalty assumptions dominate results, so the backtest must model margin and auto-deleveraging (ADL), not just funding accrual.
- The unhedged cross-sectional funding sort (Lu Lei 0.74 Sharpe if it is funding-based; Aperiodic claims) is essentially a short-crowding factor. Point-in-time tests reject it, so give it a low prior.
- Hold carry with a slow switch (weekly/monthly) to keep turnover small. The audit shows 7d vs 30d switching barely changes Sharpe (1.54-1.71), so slower is cheaper at no cost to performance.

### Gaps
- No peer-reviewed post-2022 net-of-cost estimate exists for the *cross-sectional* (unhedged) funding sort.
- The Lu Lei paper's carry definition and sample could not be verified.
- The BIS paper's predictive regressions (does high carry predict negative spot returns?) could not be read.

---

## Q4. Premium index / basis mean reversion and no-arbitrage-bound papers: tradable directional signals?

### Takeaway
The theory gives clean no-arbitrage bounds: perp price is the expected spot at a random time (Ackerer-Hugonnier-Jermann), with deviations widened by cost bounds (He-Manela-Ross-von Wachter). He et al. report "large Sharpe ratios even at the highest Binance fee tier" for a deviation-based (random-maturity) arbitrage, but deviations **shrink over time**. These are **market-neutral basis trades**, not directional signals. Short-horizon directional reversal on perps is real but only about 1.3 bp gross per trade against 5 bp round-trip, so it is untradable.

### Cited Findings
- He, Manela, Ross & von Wachter, "Fundamentals of Perpetual Futures" (arXiv 2212.06888, SSRN 4301150; revised through 2026).
  - The no-arbitrage perp price is derived, and with round-trip cost C there are no-arbitrage bounds.
  - Deviations are **far larger than in FX**, **comove across coins**, and **diminish over time**.
  - A simple random-maturity arbitrage gives large Sharpe even for the VIP1 (highest-cost) Binance tier; cost tiers are VIP1/5/8.
  - The authors note the risk of no fixed unwind date.
  — [arXiv](https://arxiv.org/abs/2212.06888); [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4301150)
- Ackerer, Hugonnier & Jermann, "Perpetual Futures Pricing" (Mathematical Finance 36(3):481-499; NBER w32936; arXiv 2310.11771).
  - Perp price equals the risk-neutral expectation of spot at a random time set by anchoring intensity κ.
  - Some funding specs make perp equal spot, and those are replicable.
  — [NBER](https://www.nber.org/papers/w32936); [arXiv](https://arxiv.org/abs/2310.11771); [EPFL one-pager](https://epfl.ch/labs/sfi-jh/wp-content/uploads/2024/10/Perp_price_one_page.pdf)
- Kim & Park, "Designing funding rates for perpetual futures" (arXiv 2506.08573, 2025) is theory on funding design. — [arXiv](https://arxiv.org/abs/2506.08573)
- Gornall-Rinaldi-Xiao: perps "reduce extreme price dislocations" and keep prices close to spot even in severe downturns. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5036933)
- arXiv 2608.21888, "Short-horizon mean reversion in cryptocurrency markets".
  - Betting against the previous candle captures the effect, which fades by about 4h and replicates on perp prices.
  - In a matched OOS test, 90% of 183 Binance pairs are significant versus 2.7% of equities, with a six-month frozen holdout.
  - Gross edge is at most **about 1.3 bp per trade vs 5 bp round-trip: not tradable.**
  — [arXiv](https://arxiv.org/abs/2608.21888)
- Presto Labs "Optimizing Funding Fee Arbitrage": practitioner write-up on timing entry/exit of funding arbitrage. — [Presto Labs PDF](https://assets.ctfassets.net/m1hizt3hapq0/2ai7mco2huKGBeWxu9wO8A/25884994fffc3f40d5f9039b44e373c5/Trading_Focus_-3_Optimizing_Funding_Fee_Arbitrage.pdf) (contents not read)

### Inferences
- The hourly premium index is the natural input for a He et al.-style rule. Proposed spec, mine and not the paper's exact rule: enter short perp / long spot when the premium exceeds the upper bound (funding interest clamp plus round-trip cost C), and exit when it reverts inside the band. Mirror for discounts, which need spot borrow or are skipped.
- That rule requires *spot* execution or borrow. With USD-M perps only, the trade is not implementable as true arbitrage. The directional residual (short the perp when the premium is extreme) is just the rejected funding-contrarian trade at a faster clock.
- A **pairs version is implementable with perps only**: relative premium between two coins, or the premium of an alt versus BTC's premium. It is unstudied in the literature, so treat it as exploratory.
- Directional one-bar reversal is ruled out at taker costs by arXiv 2608.21888 and the mtrinkner 1-day reversal result (Sharpe -1.41).

### Gaps
- He et al.'s exact entry/exit thresholds and Sharpe per cost tier and period (including post-2022) were not readable.
- No study found that tests premium-index z-score as a *directional* predictor with costs.

---

## Q5. Which of these are likely low-correlated with a long-only daily crypto trend-following strategy?

### Takeaway
Market-neutral carry and basis trades are structurally low-correlated with long-only trend. Their risk is concentrated in crash/liquidation episodes, which are exactly when trend is also hurting or flat. Cascade-reversal longs are timing-anti-correlated with trend. Most cross-sectional positioning sorts are beta-neutral but fail after costs.

### Cited Findings
- Carry/basis returns are driven by long-leverage demand from **trend-chasing** small investors. Carry is highest in bull/trend phases and is hit by margin spikes and liquidations in drawdowns. That implies *positive* regime overlap with long trend, even though returns are delta-neutral. — [BIS WP 1087](https://www.bis.org/publ/work1087.htm)
- Cross-sectional carry returns are not explained by crypto market, momentum or other factors, but load on **equity-market volatility risk**. — [Lu Lei abstract, ZUEL](https://dtf.zuel.edu.cn/szjsyxdjr-szjs_tzyg/szjsyxdjr_cont_news/details-40034.html)
- Perp drawdowns mean-revert quickly (Gornall et al.). Any reversal sleeve buys into trend-follower exits. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5036933)
- Carry Sharpe collapsed in 2025. Correlation benefits are moot if the expected return is about zero. — [arXiv 2510.14435](https://arxiv.org/pdf/2510.14435); [GitHub mtrinkner](https://github.com/mtrinkner/crypto-funding)

### Inferences
- Ranking by expected diversification value times plausibility of a positive net edge, for this project:
  1. **Alt cash-and-carry with a slow switch** (20 coins, weekly, trailing-funding gate, liquidation-aware sizing). Low daily correlation, but correlated drawdown timing with trend in crashes, and a decaying edge. Needs spot legs.
  2. **Liquidation-cascade reversal (event long/short, 4-24h)**. Timing is anti-correlated with trend exits; evidence is indirect only; small sample.
  3. **Cross-sectional basis/premium sort, weekly, beta-neutral**. Near-zero beta, but low prior given failed replications and overlap with Chi et al.
  4. **Long/short-ratio cross-sectional sort**. Unknown correlation and no prior evidence; exploratory only.
- All directional time-series funding/OI signals on BTC will tend to be **short when trend is long** (high funding and rising OI happen in uptrends). They act more like hedges with negative expected return than as diversifiers, which is consistent with the project's rejected BTC funding-contrarian test.
- A practical low-cost use: positioning variables as a **risk overlay** on the trend book rather than standalone alpha. For example, scale down trend exposure when the premium/funding z-score and the OI z-score are both above the 95th percentile, to address crash risk per BIS. This has not been tested in any found paper and must be pre-registered.

### Gaps
- No study found that reports the correlation of funding/OI/basis strategies with crypto time-series momentum.
- Data needs common to all tests:
  - spot prices for the basis/carry legs (not in the current dataset);
  - Binance historical liquidation orders (not available per arXiv 2607.27070, so use the OI-drop proxy);
  - point-in-time universe membership, to avoid the survivorship effect that killed the mtrinkner crowding IC;
  - margin and ADL modelling, so liquidation penalties are included (a 2-10% penalty swings Sharpe from +1.0 to -1.8 in the audit).

# Crypto derivatives-calendar and related systematic strategies (2019-2026): catalogue of testable rules

Scope note: research done 2026-10-15 using web search only. Direct page fetches of ScienceDirect, arXiv, Springer, SSRN and news sites failed (DNS/proxy 403 in this environment), so details come from search-result abstracts and summaries. Exact effect sizes, cost assumptions and some sample periods could not be checked against full texts; this is flagged where it applies. Project data available: Binance USD-M perps for 20 coins, 5m OHLCV + taker volume (2020-2026), OI and L/S ratios (from 2021-12), 8h funding, hourly premium index. No options data, no on-chain data.

## 1. Options-expiry effects in BTC/ETH (Deribit 08:00 UTC, max pain/pinning, dealer gamma)

### Takeaway
The best evidence is one peer-reviewed paper, Weiss, Gaudiosi, Zhou & Webb (Finance Research Letters, 2026). It documents an intraday return reversal around Deribit BTC expiries: the price drops into the 07:30-08:00 UTC settlement window and rebounds afterwards. The effect concentrates on high ATM-OI days and is strongest when dealer gamma is negative. A calendar-only version (every Friday) can be tested on our 5m data, but the paper's conditioning variables need Deribit options data we do not have. Max-pain pinning has no systematic support.

### Cited Findings
- Weiss, D., Gaudiosi, R., Zhou, Z. I., Webb, R. I. (2026), "Bitcoin option expiration, gamma exposure, and intraday price reversals", Finance Research Letters, DOI 10.1016/j.frl.2026.110340. — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1544612326008688); [ResearchGate](https://www.researchgate.net/publication/407095140_Bitcoin_option_expiration_gamma_exposure_and_intraday_price_reversals)
  - It documents a significant intraday return reversal around Deribit BTC option expirations, using spot exchange and Deribit perpetual data. The effect concentrates on days with elevated at-the-money OI and is strongest when cumulative gamma exposure is negative. — [ScienceDirect abstract via search](https://www.sciencedirect.com/science/article/pii/S1544612326008688)
  - The proposed mechanism is positive-feedback trading pressure from option market makers hedging net short exposure. Volume rises around expiry in Deribit perps and in the spot exchanges in the settlement index. The paper estimates about USD 50m per year of wealth transfer between option writers and holders. — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1544612326008688)
  - Sample: Deribit BTC options, 2021-2023. Settlement price = average of the Deribit BTC index over 07:30-08:00 UTC. Perp turnover is higher on high-OI expiry days, with the largest effect in 08:00-09:00 UTC. — [summary via search](https://www.researchgate.net/publication/407095140_Bitcoin_option_expiration_gamma_exposure_and_intraday_price_reversals)
  - Pattern described in the press: BTC tends to fall in the hour before expiry and reverse over the next ~2 hours. The gamma proxy is reconstructed from trade history, not from total OI or put/call ratio. Statistical significance is reported when ATM OI is in the top decile. — [CryptoSlate coverage](https://cryptoslate.com/bitcoins-2-24-billion-friday-options-expiry-teased-a-reversal-then-gave-it-back-within-hours/)
  - Post-publication anecdote (a single 2026 expiry): BTC fell 0.16-0.18% on three venues in the hour before 08:00 UTC. The rebound faded, and all three venues were slightly below expiry-time levels by 10:00 UTC. Public data could not confirm the paper's high-OI or negative-gamma conditions. — [CryptoSlate](https://cryptoslate.com/bitcoins-2-24-billion-friday-options-expiry-teased-a-reversal-then-gave-it-back-within-hours/); [cryptonews mirror](https://cryptonews.net/news/bitcoin/33430359/)
- Blasco, Corredor & Satrústegui (2023), "Is there an expiration effect in the bitcoin market?" covers monthly CME/CBOE/Bakkt futures expiries on 7 spot exchanges using intraday data. Volume rises before and falls after expiration, at least for cash-settled contracts. Volatility shows a similar but shorter-lived pattern. Effects on returns do not follow a common pattern, and results differ across exchanges and contracts. — [Zaguan/Unizar repository](https://zaguan.unizar.es/record/125822?ln=en); [Quantpedia summary](https://quantpedia.com/cryptocurrency-market-dynamics-around-bitcoin-futures-expiration-events/)
- Max pain: no rigorous empirical test was found. Deribit itself has said recent quarterly expiries have not consistently shown a strong pinning effect. In one June expiry, max pain was about $72k while BTC traded about $61.7k. Episodes of convergence in 2020-21 are anecdotal. — [Decrypt](https://decrypt.co/376752/billion-bitcoin-options-expire-what-it-means); [Cointelegraph](https://cointelegraph.com/news/bitcoin-above-69-000-largest-quarterly-options-expiry)
- Deribit quarterly expiry volatility impact was described by practitioners as "minor". — [Blockworks](https://blockworks.com/news/deribit-bitcoin-options-volatility-impact)

### Inferences
- **Rule E1 (calendar-only, fully testable):** Every Friday, short BTC (and ETH) perp at 07:00 UTC and cover at 08:00 UTC, then go long 08:00-10:00 UTC. Test the variants (a) all Fridays, (b) last Friday of the month, (c) quarterly Fridays (last Friday of Mar/Jun/Sep/Dec). The quarterly and monthly subsets proxy for "high OI" days because OI is concentrated there. Data: 5m OHLCV. Cost hurdle: about 2 round trips per Friday at taker fees (~4-5 bp per side on Binance), so the edge has to exceed about 16-20 bp per week. The one documented 2026 move (16-18 bp pre-expiry) is the same size as costs, so a maker-only execution is likely needed.
- **Rule E2 (vol/range proxy for gamma, testable):** Condition E1 on a pre-expiry realized-vol or taker-imbalance proxy. For example, take the trade only if Thursday 08:00 to Friday 07:00 realized vol is in the top tercile, or if perp OI on Binance is in the top quintile (available from 2021-12). This is a crude stand-in for the paper's negative-gamma condition, not a replication.
- The mechanism is intraday and Friday-only, so correlation with long-only daily trend should be near zero. Capacity per event is small, and the total annual Sharpe contribution is likely modest even if the effect is real.
- A true replication needs Deribit strike-level OI and trade history to reconstruct the gamma proxy. Tardis.dev and Deribit historical endpoints exist but are not in our dataset.

### Gaps
- Exact reversal magnitude in bp, t-stats and any strategy PnL/costs from Weiss et al. are unknown because the full text was not retrievable.
- No independent replication on 2024-2026 data was found, apart from single-event press checks.
- ETH expiry results were not found; the paper appears to be BTC-only.
- No paper on Deribit weekly versus monthly differences was found.

## 2. CME bitcoin futures gaps and CME basis

### Takeaway
CME "gap fill" claims are practitioner folklore with no peer-reviewed test found. Quoted fill rates (60-95%) are unsourced and undefined. CME moved crypto futures and options to 24/7 trading on 29 May 2026, so new weekend gaps no longer form, and the strategy is structurally dead going forward. No paper was found showing that CME basis predicts BTC returns.

### Cited Findings
- CME Group launched 24/7 crypto futures and options trading on CME Globex at 4:00 pm CT on Friday 29 May 2026. The only scheduled interruption is a Saturday 2-4 am CT maintenance window. — [The Block](https://theblock.co/post/390491/cme-group-launch-24-7-crypto-futures-options-trading-may-29); [MarketsMedia](https://www.marketsmedia.com/cme-launches-24-7-crypto-futures-options-trading/); [Bitcoin Magazine](https://bitcoinmagazine.com/news/cme-group-goes-live-with-24-7-crypto)
- With continuous trading, new weekend gaps no longer form, though existing unfilled gaps remain on charts. — [Phemex](https://phemex.com/blogs/cme-crypto-24-7-bitcoin-futures); [Yahoo Finance/CoinDesk "first gap-free Monday"](https://finance.yahoo.com/markets/crypto/articles/bitcoin-first-cme-gap-free-174649486.html)
- Fill-rate claims:
  - CoinDesk research was cited as finding that all but one of 80 gaps eventually filled. — [Cointelegraph](https://cointelegraph.com/news/largest-ever-cme-gap-has-just-printed-in-bitcoin-futures)
  - "About 77% within a week" and "65-80% in first week" come from blogs with undisclosed methods. — [Bitget wiki](https://www.bitget.com/wiki/what-is-cme-gap-in-crypto); [Phemex Academy](https://phemex.com/academy/cme-futures-gap)
  - One critical piece notes that the quoted 75-80% "rarely came with a source or a defined time window". — [fxnx](https://fxnx.com/en/blog/cme-bitcoin-gap-gone-what-changed-when-futures-went-24-7)
- Skeptic view: some argue CME gaps are a technical artifact with no predictive value. — [Blockworks](https://blockworks.co/news/bitcoin-futures-march-2023-gap)
- CME BTC "Friday futures" and market-integrity discussion. — [CF Benchmarks](https://www.cfbenchmarks.com/blog/cme-bitcoin-friday-futures-predictability-accessibility-market-integrity)

### Inferences
- A high "eventual" fill rate is near-tautological for a volatile random walk: almost any nearby level is revisited eventually. The only testable version is time-bounded and benchmarked against a random-level null.
- **Rule G1 (historical only, proxy):** On Sunday 22:00 UTC (the old CME reopen), compute the gap = Binance BTC perp price minus Binance price at Friday 21:00 UTC (the CME close proxy; CME settles about 20:00 UTC, adjust for DST). If |gap| > 1%, trade toward the Friday-close level, with target = Friday close, stop = 1x gap beyond entry, and a time stop of 5 days. Compare the hit rate against random levels at equal distance. Data: 5m perps. This is only relevant for 2020 to May 2026, so it is a low-priority test with no live applicability after the 24/7 switch.
- CME basis needs CME futures data, which we do not have. The Binance hourly premium index is a substitute for perp basis and is already covered by the project's premium-carry work.

### Gaps
- No academic study of CME gaps or CME basis predictability (2019-2026) was found.
- It is unknown whether the Saturday maintenance window produces micro-gaps worth anything (very likely not).

## 3. Stablecoin flows / exchange netflows as short-horizon predictors

### Takeaway
There is academic support. Chi, Chu & Hao (arXiv 2411.06327, revised Sep 2025) find that USDT net exchange inflows positively predict BTC/ETH returns at 1-2h horizons. Ante, Fiedler & Strehle (FRL 2021) find that stablecoin issuances follow downturns and precede positive abnormal returns. Both need on-chain data we do not have. The issuance/mint signal can in principle be built from free public blockchain explorers (Tether treasury mints on Ethereum/Tron), but exchange netflows realistically need a paid provider (CryptoQuant/Glassnode).

### Cited Findings
- Chi, Y., Chu, Q. (R.), Hao, W., "Return and Volatility Forecasting Using On-Chain Flows in Cryptocurrency Markets", arXiv:2411.06327 (2024, revised Sep 2025). Authors are from the University of Auckland and NTU. — [arXiv](https://arxiv.org/pdf/2411.06327); [IDEAS/RePEc](https://ideas.repec.org/p/arx/papers/2411.06327.html)
  - USDT net inflows positively predict ETH and BTC returns at 1h and 2h intervals, and negatively predict ETH/BTC volatility at 6h. — [arXiv](https://arxiv.org/pdf/2411.06327)
  - ETH net inflows strongly predict ETH returns and volatility (2017-2023). BTC net inflows mostly lack return predictability (except at 4h) but are negatively associated with volatility. — [IDEAS summary](https://ideas.repec.org/p/arx/papers/2411.06327.html)
  - It includes in-sample/out-of-sample regressions plus trading and option-strategy tests. The specific Sharpe and costs could not be retrieved.
- Ante, L., Fiedler, I., Strehle, E. (2021), "The influence of stablecoin issuances on cryptocurrency markets", Finance Research Letters 41, DOI 10.1016/j.frl.2020.101867. — [BRL working paper PDF](https://www.blockchainresearchlab.org/wp-content/uploads/2020/05/The_Influence_of_Stablecoin_Issuances_on_Cryptocurrency_Markets_BRL_Working_Paper_No_11.pdf); [IDEAS](https://ideas.repec.org/a/eee/finlet/v41y2021ics1544612320316810.html)
  - Event study of 565 issuances of at least $1m across 7 stablecoins, Apr 2019 to Mar 2020. Issuances follow market downturns. There is a positive abnormal BTC return in the 24h around issuance (USDT: before the event; HUSD/BUSD: after). Size does not matter. Abnormal is measured relative to the prior-week mean, not an absolute positive return. — [BRL blog summary](https://www.blockchainresearchlab.org/2020/06/24/how-do-stablecoin-issuances-affect-cryptocurrency-markets/)
- Practitioner claims (BofA note, Santiment, FXStreet) are anecdotal. — [Decrypt/BofA](https://decrypt.co/110549/stablecoin-flows-crypto-market-recovery-bank-america); [Santiment](https://insights.santiment.net/read/could-this-metric-be-propping-up-btc's-recovery%3F-6218)
- Artemis: stablecoin flows between chains predict cross-sectional L1 returns (practitioner factor note). — [Artemis](https://research.artemisanalytics.com/p/crypto-factor-model-analysis-launching-ae0)

### Inferences
- **Rule S1 (needs on-chain data; free with effort):** When a USDT treasury mint of at least $X occurs (from Etherscan/Tronscan treasury address transfers), go long BTC perp for 24h. The Ante et al. finding is that the effect is mostly before the event for USDT, which makes this weak and possibly already priced in. This is not testable with current data.
- **Rule S2 (needs paid exchange-netflow data):** Go long BTC/ETH for 1-2h when hourly USDT net exchange inflow is in its top decile. This requires labelled exchange wallets (CryptoQuant/Glassnode/Arkham), so it is not implementable with free public data at reasonable effort.
- **Partial proxy (testable now):** Binance taker buy volume and premium index capture the execution side of stablecoin deployment. This overlaps with already-tested premium/positioning signals.

### Gaps
- No out-of-sample net-of-cost Sharpe was retrievable for Chi et al.
- No post-2020 replication of the issuance event study was found.

## 4. Volatility-managed crypto trend and risk-parity across crypto sleeves

### Takeaway
Volatility scaling reliably reduces crash risk in crypto momentum (Grobys et al. 2025). It is an overlay that can improve the existing trend book rather than a new uncorrelated return source. Diversified (hierarchical) risk parity across coins performed badly post-COVID (HRP variants lost 51-64%), and edges are fragile under search-adjusted inference (Matys et al. 2026). Risk parity across strategy sleeves (trend, carry, cascade) is not studied in the crypto literature found.

### Cited Findings
- Grobys, K., Kolari, J. W., Sandretto, ?, Shahzad, ?, Äijö, J. (2025), "Cryptocurrency momentum has (not) its moments", Financial Markets and Portfolio Management, DOI 10.1007/s11408-025-00474-9, open access. Volatility scaling reduces crash risk of crypto momentum in large caps, consistent with equity evidence. — [Springer](https://link.springer.com/article/10.1007/s11408-025-00474-9); [Uni Vaasa repository](https://osuva.uwasa.fi/handle/10024/20018)
- "Low-volatility strategies for highly liquid cryptocurrencies", FRL 2021 (DOI 10.1016/j.frl.2021.102422). Concentrated low-vol portfolios of liquid coins (Jan 2017 to Jun 2021) earn significant excess returns with 6-12 month look-back and holding periods, and a stop-loss improves Sharpe. — [ZHAW repository](https://srv-clst-301-data66.zhaw.ch/handle/11475/23853)
- Matys, Rodriguez & Delfau (2026, CEMA working paper 928): 27 allocation strategies on a survivorship-bias-corrected Binance universe. Diversified HRP lost 51-64% post-COVID, BTC-concentrated allocators held up better, and edges are statistically fragile under search-adjusted inference. — [IDEAS](https://ideas.repec.org/p/cem/doctra/928.html)
- Barbon (working paper, "Catching Crypto Trends"): Donchian-channel trend with vol-based sizing on a top-20 rotational portfolio, reported Sharpe above 1.5 net of fees, robust beyond BTC. — [abarbon.com](https://abarbon.com/papers/catching-crypto-trends)
- Bui & Nguyen (arXiv 2602.11708, Feb 2026), "AdaptiveTrend": 6h trend signals with monthly construction, reported Sharpe 2.41 and MDD -12.7% over 2022-2024. This is an unreviewed preprint with a short window. — [arXiv](https://arxiv.org/abs/2602.11708v1)
- Monash project notes that transaction costs from frequent rebalancing reduce trend profits. — [Monash CFS](https://www.monash.edu/business/monash-centre-for-financial-studies/our-research/all-projects/investment-strategy/trend-following-strategies-for-crypto-investors)

### Inferences
- **Rule V1 (overlay, testable):** Scale each trend sleeve's weight by target_vol / realized_vol, using 20-30d realized vol from daily or 5m-aggregated returns, capped at 2x. This should cut drawdowns but leaves correlation to long-only trend about the same, so it does not meet the low-correlation priority.
- **Rule V2 (sleeve risk parity, testable):** Use inverse-vol or equal-risk-contribution weights across the existing accepted sleeves (premium carry XS, liquidation-cascade buy, trend), with 60d covariance, monthly rebalance. This is portfolio construction, not alpha. The literature suggests coin-level HRP is unhelpful, while sleeve-level risk parity is untested in papers.
- **Rule V3 (low-vol XS, testable):** Each month, rank the 20 coins by 90-180d realized vol and go long the lowest-vol quintile / short the highest-vol quintile (beta-neutral). This is moderately uncorrelated to long-only trend. Out-of-sample 2022-2026 evidence for it was not found.

### Gaps
- Exact vol-scaled versus raw Sharpe numbers from Grobys et al. were not retrieved.
- No paper on volatility-regime switching (e.g., trade trend only when vol is in a given regime) with post-2022 OOS evidence was found.

## 5. Daily mean-reversion after extreme moves that survived 2022-2026

### Takeaway
Academic reversal evidence is strongest in illiquid small coins. Large, liquid coins tend to show daily momentum, not reversal (Zaremba et al. 2021). Bitcoin reversion is documented at 1-4h horizons (De Nicola 2021), and a 2026 preprint finds sign reversal in 98% of 183 crypto pairs at short horizons. The only overreaction study that tested a counter-move strategy on large coins found it was not profitable. No study showing a daily large-cap reversal surviving 2022-2026 net of costs was found. The project's liquidation-cascade buy already harvests the intraday version.

### Cited Findings
- Zaremba, A. et al. (2021), International Review of Financial Analysis. Daily data on more than 3,600 coins: low previous-day return outperforms. Reversals come from illiquidity, and the largest, most liquid coins show daily momentum instead. — [summary via Medeniyet repository](https://earsiv.medeniyet.edu.tr/items/23a96c9f-3952-4bdf-aec5-abafb3aaab70)
- Kozlowski, Puleo & Zhou (2020), Applied Economics Letters: reversals at daily, weekly and monthly horizons in 200 coins (2015-2019), strongest in small and illiquid coins. — [Fairfield](https://fairfield.elsevierpure.com/en/publications/cryptocurrency-return-reversals/)
- Kellner & Maltritz (2022), Journal of Economic Studies: short-term overreactions in 50 coins (2015-2020). Higher initial abnormal returns relate to larger inefficiencies. — [Emerald](https://emerald.com/insight/content/doi/10.1108/JES-09-2021-0488/full/pdf)
- Caporale & Plastun (CESifo WP 6861 / Brunel): BTC/LTC/XRP/DASH. Next-day moves after overreactions are larger, but a counter-movement strategy was not profitable. — [CESifo](https://cesifo.org/DocDL/cesifo1_wp6861.pdf)
- De Nicola (2021), "On the Intraday Behavior of Bitcoin", Ledger: negative first-order autocorrelation at 1h/2h/4h, with larger moves producing stronger reversals. Attributed to overreaction and leverage liquidation cascades. — [Ledger](https://ledger.pitt.edu/ojs/ledger/article/view/213); [LMU epub](https://epub.ub.uni-muenchen.de/97651/)
- Asymmetric mean reversion in BTC: stronger after negative returns. — [Sheffield Hallam](https://shura.shu.ac.uk/23470/1/Asymmetric_Mean_Reversion_of_Bitcoin_Price_Returns.pdf)
- arXiv 2608.21888 (2026), "Short-horizon mean reversion in cryptocurrency markets: a matched cross-market measurement": negative sign-correlation in 98% of 183 crypto pairs versus 50% of stocks. — [arXiv](https://arxiv.org/pdf/2608.21888)
- Cost failure example: a blog shows a cross-sectional reversal signal going from gross Sharpe ~13 to ~-40 at 10 bp per side. — [DEV Community](https://dev.to/pavel_kkkkazantsev/my-crypto-backtest-had-a-sharpe-of-134-then-i-added-trading-costs-5718)

### Inferences
- For our 20 large coins, daily XS reversal is unlikely to work (Zaremba et al.: large caps show momentum). An intraday time-series reversal after large 1-4h moves is better supported (De Nicola, arXiv 2608.21888), but it overlaps heavily with the cascade-buy sleeve.
- **Rule M1 (testable, possibly novel versus cascade):** An upside-reversal (short) version. After a 4h return above +3 sigma (using 30d 4h-vol), short for 4-8h. This is the mirror of the cascade-buy, and the asymmetry literature suggests it is weaker, so treat it as low prior.
- **Rule M2 (testable):** Market-neutral intraday XS reversal. Every 4h, go long the bottom 3 / short the top 3 of the 20 coins by trailing 4h residual return (after BTC beta). This is very cost-sensitive: require maker execution and evaluate at 4-5 bp per side.

### Gaps
- No 2022-2026 out-of-sample daily reversal result for large caps was found.
- Full-text details of De Nicola's trading-strategy backtest are unavailable.

## 6. Market-neutral crypto perp strategies with reported net Sharpe > 1 out of sample

### Takeaway
Credible net-Sharpe > 1 results come mainly from perp-spot no-arbitrage (He, Manela, Ross & von Wachter): Sharpe 1.8 for BTC at retail costs, but this needs spot plus perp and is basis/funding arbitrage close to what the project already runs. Most independent 2022-2026 replications of cross-sectional perp factors (momentum, OHLCV/funding ML) find net Sharpe of zero or below. One SSRN paper claims Sharpe 1.45 with an own-history ranking, but its details are unverified.

### Cited Findings
- He, S., Manela, A., Ross, O., von Wachter, V., "Fundamentals of Perpetual Futures", arXiv 2212.06888 (2022, revised through v7). — [arXiv v7](https://arxiv.org/html/2212.06888v7)
  - The strategy trades perp versus spot deviations from no-arbitrage. BTC Sharpe is 1.8 at high retail costs and up to 3.5 for zero-fee market makers. — [arXiv](https://arxiv.org/abs/2212.06888v6)
  - Deviations comove across coins and diminish over time, suggesting decay. Whether results are out of sample is unclear.
- Arefev, O. (SSRN 7404139), "Cross-Sectional Momentum in Cryptocurrency: A Net-of-Costs Replication on Tradable Binance Perpetuals (2020-2026)": neither pre-committed momentum spec has a net spread distinguishable from zero. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7404139)
- Junior, A. F. (SSRN 6701738), "Failure of Cross-Sectional Alpha Screening on Cryptocurrency Perpetual Futures": 10 Binance USDT perps, Jul 2022 to Apr 2026, purged walk-forward. The best model has weakly positive rank IC but negative net Sharpe, and there is no exploitable 8h XS alpha from OHLCV/funding signals. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6701738)
- Dhanya MD (SSRN 7301919), "Every Asset Its Own Benchmark: Market-Neutral Alpha in Perpetual Futures": 10 equity-derived factors on 112 perps over 363 weeks. Ranking each asset against its own history raises mean annual Sharpe from 1.01 to 1.45, and the paper claims robustness to 4x costs and a deflated-Sharpe correction. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7301919) (a second search could not confirm details; treat as unverified)
- Frontiers in Blockchain (2026): minute-level microstructure signals have deeply negative net Sharpe after turnover costs. — [Frontiers](https://www.frontiersin.org/journals/blockchain/articles/10.3389/fbloc.2026.1811716/full)
- BIS WP 1087 "Crypto carry": carry (futures/perp basis) is large and predicts crash risk. — [BIS](https://www.bis.org/publ/work1087.pdf)

### Inferences
- **Rule N1 (testable now):** The "own-history" rank transform from Dhanya MD. For each coin, z-score a factor (e.g., 7d return, 30d vol, taker-buy ratio, premium) against that coin's own 1-year history. Then rank the cross-section on the z-scores, go long the top 4 / short the bottom 4, rebalance weekly, beta-neutral. This is cheap to test on existing data and plausibly low-correlation to long-only trend. Pre-register specs because of the replication failures above.
- **Rule N2 (needs spot data):** Perp minus spot no-arbitrage band trade (He et al.). Our hourly premium index proxies the deviation, but executing the hedge needs spot. This is likely redundant with the accepted premium-carry XS sleeve.
- The weight of evidence (Arefev, Junior, Frontiers) says naive XS perp factors on Binance do not survive costs in 2022-2026. Prior for any new XS factor reaching net Sharpe > 1 should be low.

### Gaps
- No paper with clearly out-of-sample (post-publication) net Sharpe > 1 for a market-neutral perp strategy was verified.
- Cost assumptions in the SSRN papers were not retrievable.

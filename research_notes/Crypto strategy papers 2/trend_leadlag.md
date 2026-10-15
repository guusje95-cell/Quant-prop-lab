# Crypto intraday/multi-hour trend, BTC->alt lead-lag, cross-asset lead-lag, and 2022 bear-market strategies

Method note: WebSearch worked, but every WebFetch failed with DNS errors (ssrn, springer, arxiv, concretumgroup, monash, centaur.reading.ac.uk). So the findings below come from search-result abstracts and summaries, not full-text reads. Exact parameter tables, cost sensitivities and per-year (2022) splits could not be extracted and are listed under Gaps. Treat any number below as "abstract-level".

## Q1. Which intraday/multi-hour trend designs on crypto have net-of-cost evidence, and how do they correlate with daily trend-following?

### Takeaway
The best-documented multi-hour trend evidence is practitioner work by Concretum (Zarattini/Pagani/Barbon). Their daily Donchian ensemble has net-of-fee evidence: Sharpe about 1.5, near-zero correlation with the SG Trend index. Their intraday long-short ensemble has only gross evidence: Sharpe about 1.6 over 2018-2025. A 2026 arXiv preprint (6-hour signals, 70/30 long-short, out-of-sample 2022-2024) claims Sharpe 2.41 but has not been replicated. Academic "intraday TSMOM" on BTC (Shen, Urquhart and Wang 2022) is the first/last half-hour effect, which this project already rejected. I found no peer-reviewed 1h/4h/12h trend paper with net-of-cost results on perps.

### Cited Findings
- **Concretum, "Catching Crypto Trends: A Tactical Approach for Bitcoin and Altcoins" (Zarattini, Pagani, Barbon; SSRN 2025).** Daily bars. Ensemble of nine Donchian-channel lookbacks with a trailing-stop exit. Positions are volatility-sized to a 25% annualised target.
  - BTC since 2015: net-of-fee CAGR about 30%, Sharpe 1.56, max drawdown about 19%. Passive BTC drawdowns exceeded 80% over the same period.
  - Monthly rotation across liquid altcoins: about 18% net CAGR.
  - Rolling correlation with the SG Trend Index averages about 7.4%.
  - Sources: [Concretum Substack summary](https://concretumgroup.substack.com/p/catching-crypto-trends); [Concretum paper page](https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/); [Barbon paper page](https://abarbon.com/papers/catching-crypto-trends)
  - The individual lookback values and the fee level were not extracted.
- **Concretum, "Seasonality in Bitcoin Intraday Trend Trading" (Zarattini, Pagani, Barbon).** Long-short portfolio built from an ensemble of several high-frequency trend-following models on BTC. Volatility-scaled to 20% annualised.
  - 2018-2025: gross-of-fees Sharpe about 1.6.
  - Benchmark: a long-only BTC position scaled to 20% volatility had Sharpe just below 0.8.
  - The article's focus is on which hours of the day carry the intraday trend P&L.
  - No net-of-fee Sharpe was visible in the snippets.
  - Sources: [Concretum](https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/); [Concretum Pills #16](https://concretumgroup.substack.com/p/concretum-pills-16)
- **Bui and Nguyen (Talyxion Research), "Systematic Trend-Following with Adaptive Portfolio Construction: Enhancing Risk-Adjusted Alpha in Cryptocurrency Markets", arXiv:2602.11708 (Feb 2026).**
  - Design:
    - 6-hour trend signals.
    - Volatility-calibrated trailing stop.
    - Monthly rebalancing, with asset selection by rolling Sharpe and a market-cap filter.
    - Asymmetric 70% long / 30% short capital split.
    - Universe of more than 150 pairs.
  - Out-of-sample results over 36 months (2022-2024): Sharpe 2.41, max drawdown -12.7%, Calmar 3.18.
  - Claims to beat a TSMOM benchmark and equal-weight buy-and-hold.
  - Says it ran robustness checks on parameters and costs; the details were not seen.
  - Single small-firm preprint, unreplicated.
  - Source: [arXiv abs](https://arxiv.org/abs/2602.11708); [html](https://arxiv.org/html/2602.11708v1)
- **Shen, Urquhart and Wang (2022), "Bitcoin intraday time series momentum", *Financial Review* 57(2):319-344.**
  - The first half-hour return predicts the last half-hour return, with the trading day defined by volume.
  - The authors attribute the effect to liquidity provision, and say it is stronger in downturns and after high-volume or high-volatility opening sessions.
  - This is the "Gao first/last half-hour" family already rejected in this project.
  - Sources: [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/fire.12290); [CentAUR accepted version](https://centaur.reading.ac.uk/100181/)
- **JRFM 2025, "On the Performance of Lagged Momentum and Reversal Strategies Across Daytime and Overnight Sessions in Bitcoin and Ethereum".** Hourly BTC/ETH, 2016-2025. Results depend heavily on how the day is split into sessions, which points to a data-mining risk for session-based rules. [MDPI/JRFM](https://doi.org/10.3390/jrfm19090692)
- **Padysak and Vojtko (2022), "Seasonality, Trend-following, and Mean Reversion in Bitcoin".**
  - Hourly data, 2015-2022.
  - The paper is cited for the 21:00-23:00 UTC effect, which this project already rejected.
  - It also tests a MAX/MIN breakout trend rule and a mean-reversion rule, but I could not retrieve their parameters.
  - Source: secondary summary at [PapersWithBacktest](https://paperswithbacktest.com/blog/bitcoin-never-sleeps-exploiting-seasonality)
- **Le and Ruthbah (Monash Centre for Financial Studies, Aug 2024), "Trend-following Strategies for Crypto Investors".**
  - Rules: hold BTC, ETH or the S&P crypto large-cap index when the prior-day price is above its 20/65/150/200-day SMA; otherwise hold cash.
  - Costs tested at 0.1%, 0.25% and 0.5% per trade.
  - Shorter lookbacks give a higher Sharpe, but turnover costs erode the gain.
  - Reports negative strategy returns April-December 2022 except July and October. This is a long/cash design, so it has no short side.
  - Sources: [Monash project page](https://www.monash.edu/business/mcfs/our-research/all-projects/investment-strategy/trend-following-strategies-for-crypto-investors); [CXO Advisory summary](https://www.cxoadvisory.com/technical-trading/applying-simple-trend-following-rules-to-cryptocurrencies)
- **Man Group, "In Crypto We Trend" (practitioner).** Argues crypto suits trend-following, and that running trend on 10-15 coins balances diversification against costs. High correlations between coins limit diversification. Source: secondary summary at [The Idea Farm](https://theideafarm.com/alternative-investment/real-assets/crypto/in-crypto-we-trend/); original at [man.com](https://www.man.com/insights/in-crypto-we-trend)
- **Bloomberg (27 Feb 2026).** Choppy markets punished crypto trend-following funds in 2025, and the trade found relief after a sharp selloff in early 2026. This means recent live performance has been weak. [Bloomberg](https://www.bloomberg.com/news/articles/2026-02-27/crypto-trend-following-trade-finds-relief-after-sharp-selloff)
- **GitHub research plan (not evidence).** Specifies a 4-hour Donchian family with lookbacks of 20/55/120 bars and trailing exits, tested net of 11 bp round trip plus funding, against a volatility-targeted buy-and-hold control. Useful as a protocol template only. [GitHub issue](https://github.com/ibrahimjaved12/crypto-watcher/issues/222)

### Inferences
- **Testable rule T1 (Concretum-style intraday ensemble, adapted to this dataset).**
  - Signals: on 1h and 4h bars, compute Donchian breakout signals over several lookbacks (for example 1h × {24, 48, 96, 168, 336} bars and 4h × {20, 42, 84} bars).
  - Positions: each sub-signal is +1/-1/0 with a trailing exit at the mid-channel or the opposite half-channel. Average the sub-signals into a score in [-1, 1].
  - Sizing: score × (target vol / realised vol), with realised vol from an EWMA of 1h returns over about 30 days and a target of 20% annualised.
  - Universe: BTC/ETH/SOL first, then the 20 coins.
  - Data needed: OHLCV only (5m resampled), plus funding for perp P&L.
  - Ensembling should reduce the parameter-picking risk in the current single (20/10) 4h breakout.
- **Testable rule T2 (Bui-Nguyen-style 6h trend).**
  - 6h bars, trend signal with an ATR-scaled trailing stop.
  - Monthly selection of the top-N coins by trailing Sharpe of the trend sleeve.
  - 70/30 long/short capital split.
  - Its out-of-sample window (2022-2024) starts with the 2022 bear market, so the short book probably drove part of the result. Test it per year.
- **Correlation with daily trend.** Concretum's daily ensemble is roughly uncorrelated with traditional CTAs (about 7%). Within crypto, 4h trend and daily trend share the same large moves, so expect their correlation to be high (unverified; no source gave a number). The diversifying part is likely the faster 1h component and its time-of-day concentration. Measure this directly with the corr(T1-1h, T1-daily) of daily P&L.
- **Costs.** With 5 bp taker, a 1h ensemble with averaged signals turns over far less than any single fast rule. A gross Sharpe of 1.6 is meaningful only if annual turnover is around 50-100× notional or less. That is a rough calculation, not sourced.

### Gaps
- Concretum's intraday paper: exact lookbacks, net-of-fee Sharpe, 2022 return and hour-of-day breakdown were not retrieved (fetch blocked).
- Bui and Nguyen: exact 6h signal definition, cost assumptions and 2022-only results were not retrieved.
- I found no published 1h/4h/12h trend study on Binance perps that reports results net of funding, and no independent replication of any of the above.
- The parameters of the Padysak and Vojtko MAX/MIN breakout rule were not found.

## Q2. Is BTC->altcoin lead-lag exploitable after ~5 bp taker / ~2 bp maker costs, and at what horizon?

### Takeaway
Lagged returns of other coins, mainly BTC and large caps, predict focal-coin returns at the minute level, up to about 10 minutes (Guo, Sang, Tu and Wang, JEDC 2024). A long-short portfolio on this signal is reported as profitable out of sample after costs, though the exact cost level was not seen. At the 1-hour horizon on recent (2024-2026) Binance data, the effect is essentially zero for large alts: next-hour correlation is about 0.006, and no Granger lead survives correction. Small caps lag more. For the 20 large perps at 5 bp taker, the edge is probably not tradable at ≥1h. Minute-level maker-execution designs are the only plausible route.

### Cited Findings
- **Guo, Sang, Tu and Wang (2024), "Cross-cryptocurrency return predictability", *Journal of Economic Dynamics and Control* 163:104863.**
  - Binance data.
  - Lagged returns of other cryptocurrencies significantly predict focal-coin returns. This holds under adaptive LASSO and PCA.
  - A long-short portfolio sorted on predicted returns earns sizable out-of-sample returns after transaction costs.
  - Mechanism: common shocks combined with limited investor attention cause slow information diffusion across coins.
  - The 2021 SSRN working-paper version says predictability holds at minute frequency for up to about 10 minutes.
  - Sources: [RePEc](https://ideas.repec.org/a/eee/dyncon/v163y2024ics0165188924000551.html); [Bristol](https://research-information.bris.ac.uk/en/publications/cross-cryptocurrency-return-predictability/); [SMU](https://ink.library.smu.edu.sg/lkcsb_research/6901)
  - Not extracted: the cost level, BTC's specific weight as a predictor, and post-2021 decay.
- **Khan (SSRN 2026), "Co-movement Without Leadership: Bitcoin's Regime-Level Influence on Altcoins, and Why Its Predictability Is Not Profitability".**
  - Binance 2024-2026, BTC plus 9 altcoins.
  - Next-hour lead correlation about 0.006.
  - Holm-corrected Granger tests leave no robust one-way hourly lead.
  - BTC's influence works through shared regimes and co-movement rather than tradable leadership.
  - Very recent preprint.
  - Source: [SSRN 7485359](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7485359)
- **"Price Transmission from Bitcoin to Altcoins: High-Frequency Evidence and Implications for Trading Strategy", *Asia-Pacific Financial Markets* (Springer, 2026).**
  - Unidirectional Granger causality from BTC to alts.
  - Small-cap coins show significant delayed responses to BTC moves.
  - An ML-based lag strategy beats buy-and-hold.
  - The cost treatment was not visible, and beating buy-and-hold is a weak benchmark.
  - Source: [Springer](https://link.springer.com/article/10.1007/s10690-026-09589-z)
- **"Does Bitcoin still own the dominant power? An intraday analysis" (NJIT).** BTC carries nonlinear predictive information for other coins in both rising and falling markets. [NJIT](https://researchwith.njit.edu/en/publications/does-bitcoin-still-own-the-dominant-power-an-intraday-analysis/)
- **"Lead-lag relationship between Bitcoin and Ethereum: Evidence from hourly and daily data", *Research in International Business and Finance* (2019).** An early hourly BTC-ETH study; its direction was not visible in the snippet. [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0275531919300522)
- **Within-BTC cross-exchange lead-lag.** Measured in seconds (up to about 15 s) in a CBS thesis. [CBS thesis PDF](https://kryptografen.no/wp-content/uploads/2019/06/High-Frequency-Lead-Lag-Relationships-in-The-Bitcoin-Market.pdf)
- **"Bitcoin at High Frequency" (JRFM 2019).** BTC returns are predictable at sampling frequencies up to about 6 hours, but not at daily or longer frequencies. [MDPI](https://www.mdpi.com/1911-8074/12/1/36)

### Inferences
- **Testable rule L1 (minute-horizon, maker-only).**
  - Signal: on 5m bars (the finest available here), regress each alt's next-5m return on BTC's and ETH's last 1-3 five-minute returns, minus the alt's own beta-adjusted move.
  - Trade only when the predicted move exceeds about 2× the round-trip maker cost (about 4 bp).
  - Use the taker-volume imbalance of BTC as a conditioning variable.
  - Main caveat: Guo et al. put the effect at ≤10 minutes. At 5m granularity, most of the predictability is already used up within the first bar. A taker round trip costs about 10 bp, which is likely larger than the expected per-trade edge for large alts. This is an inference, but consistent with Khan's near-zero hourly result.
- **Testable rule L2 ("catch-up" after large BTC moves).**
  - Trigger: BTC moves more than k·σ over 15-60 minutes.
  - Trade: go long or short the alts with the lowest realised beta-adjusted response so far. Hold 15-60 minutes.
  - Small caps lag most (per the Springer paper), but the 20-coin universe holds only large caps, so expect the effect to be weak.
- **Verdict for the brief.** Not tradable at ≥1h for large perps. At 5-15 minutes it might work with maker execution, but 5m bars cannot resolve the ≤10-minute effect cleanly. A proper test needs 1m or trade-level data.

### Gaps
- No source gave net-of-cost Sharpe for a BTC->alt rule at a stated bp cost on perps.
- The decay of the Guo et al. effect after 2021 is unknown.

## Q3. Cross-asset lead-lag from S&P/Nasdaq futures or DXY to crypto intraday

### Takeaway
I found no paper documenting a tradable minute- or hour-level lead from ES/NQ futures or DXY to BTC. The literature covers volatility and jump spillovers, overreaction after large equity moves, and the US-open volatility concentration. It does not provide directional lead-lag rules with net-of-cost results. This area is under-researched, and the testing data (crypto only) would need ES/NQ/DXY intraday data added.

### Cited Findings
- **"Bitcoin market reactions to large price swings of international stock markets" (*International Review of Economics & Finance*, 2023).** Minute-level BTC data. Large stock-market swings are followed by intraday BTC reversals in the opposite direction, which the authors read as overreaction. The effect is stronger for developed markets. [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1059056023004446)
- **Leong et al. (2025), "Bitcoin spillovers: A high-frequency cross-asset analysis", *Financial Review*.** High-frequency data show positive jump and diffusion spillovers from BTC to US equity sectors (financials, tech, consumer discretionary, communications). The direction runs BTC to equities, not the reverse. [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/fire.12418)
- **"Bitcoin on Wall Street Time" (preprint).** BTC intraday volatility moves with the US equity session across daylight-saving shifts (2016-2018 vs 2022-2025), evidence that BTC has been institutionalised around US hours. [ResearchGate](https://www.researchgate.net/publication/414091987_Bitcoin_on_Wall_Street_Time_Natural_Experiments_on_the_Institutionalization_of_a_247_Market)
- **Eross et al., "The intraday dynamics of bitcoin".** 5-minute Bitstamp data. BTC realised volatility and liquidity peak around the openings of the major stock markets. [CentAUR](https://centaur.reading.ac.uk/81745/3/2.R&R.Manuscript.pdf)
- **SEC filing (NYSE Arca, 2021), "Examining Lead-Lag Relationships Between the Bitcoin Futures and Spot Market".** CME BTC futures led all 10 evaluated spot venues. This is within-BTC, not cross-asset. [SEC](https://www.sec.gov/files/rules/sro/nysearca/2021/34-93445-ex3a.pdf)

### Inferences
- **Testable rule X1 (needs external data).**
  - Signal: during US cash hours, the ES or NQ 5-15 minute return z-score.
  - Trade: BTC/ETH perps in the same direction, holding 15-60 minutes. This tests the hypothesis that equities lead crypto.
  - Version X1b: fade, per the IREF overreaction finding, after equity moves above 2σ.
  - Data needed: 1m/5m ES and NQ futures (CME), DXY or 6E futures.
  - Priority: low. There is no published evidence of a tradable edge, and correlations are regime-dependent.

### Gaps
- No study found on DXY to crypto at intraday horizons.
- No net-of-cost cross-asset lead-lag result found.

## Q4. What worked in 2022 for crypto systematic funds (fund letters, CTA reports)?

### Takeaway
Aggregate crypto hedge funds lost about 53.5% in 2022 against about -64% for BTC. Quant and market-neutral funds had much smaller drawdowns, and some (Pythagoras market-neutral and trend funds) were reportedly up about 8%. Traditional CTAs/trend had a historic year (SG Trend +27.4%), but crypto long/cash trend rules lost money from April to December 2022. Positive 2022 crypto outcomes therefore required either a short side or market-neutral construction. Strategy-level public data are thin.

### Cited Findings
- **Crypto Fund Research index.** Crypto funds -53.5% in 2022 vs about -64.2% for BTC. In both 2018 and 2022, funds matched BTC or lost slightly less. [Crypto Fund Research](https://cryptofundresearch.com/crypto-hedge-fund-performance/)
- **Pythagoras (Bloomberg, 4 Dec 2022).** Two Pythagoras crypto funds, running market-neutral and trend-following strategies, were up about 8% in 2022. Only the headline was seen. [Bloomberg](https://www.bloomberg.com/news/articles/2022-12-04/two-pythagoras-crypto-hedge-funds-see-8-performance-gains-in-2022)
- **Galaxy VisionTrack 2023 report.** Quant funds had smaller drawdowns than directional strategies in 2022, and allocator demand for market-neutral strategies grew. [Galaxy VisionTrack 2023 PDF](https://assets.ctfassets.net/yksdf0mjii3y/3eCgzh5bw0rFWveA57KuOF/54f57fd73eca69404a781916e94e4ff1/GLXY_2023_Whitepaper_VisionTrack.pdf)
- **PwC Global Crypto Hedge Fund Reports.** The 2022 report has market-neutral as the most common strategy at about 30%; the 2023 report says about 20%. [PwC 2022](https://www.pwc.com/gx/en/financial-services/pdf/4th-annual-global-crypto-hedge-fund-report-june-2022.pdf); [PwC 2023 press release](https://www.pwc.com/gx/en/news-room/press-releases/2023/pwc-2023-global-crypto-hedge-fund-report.html)
- **Traditional trend in 2022.** Average +27.3%, SG Trend Index +27.4%, Lynx +36.8%, Transtrend +16.4%. [Alternative Fund Insight](https://alternativefundinsight.com/trend-followers-make-27-in-historic-2022/)
- **Man AHL.** Traded crypto futures within AHL and was preparing a dedicated crypto fund in November 2022. No crypto-specific 2022 return was published in the results. [The Block](https://www.theblock.co/post/188445/man-group-close-to-launching-crypto-hedge-fund-despite-ftx-collapse-bloomberg-188445)
- **Long/cash crypto trend in 2022 (Le and Ruthbah).** Negative returns April-December 2022 except July and October. [Monash](https://www.monash.edu/business/mcfs/our-research/all-projects/investment-strategy/trend-following-strategies-for-crypto-investors)
- **Bui and Nguyen.** Their out-of-sample window starting in 2022 shows Sharpe 2.41 with a 30% short sleeve. A per-year 2022 figure was not seen. [arXiv](https://arxiv.org/abs/2602.11708)
- **Shorting costs.** Crypto's upward drift, borrow costs and violent squeezes make systematic shorting expensive. Practitioner blog, low weight. [Summit Ward](https://summitward.com/learn/crypto-trend-following)

### Inferences
- A long-short trend design (Concretum's intraday ensemble, Bui and Nguyen's 70/30) is the published way trend could make money in 2022. Long/cash designs only reduced losses.
- The project's rejected "bear short sleeve (BTC < 200d MA)" was a slow regime filter. Faster 4h/6h short signals with trailing stops differ materially and are not covered by that rejection, but treat this as a hypothesis.
- Market-neutral funds earned in 2022 largely through basis/funding carry and arbitrage, per industry reports in general. These sources did not break returns down further, and the carry variants are already rejected in this project.
- **Evaluation protocol for the current candidate (4h 20/10 breakout, BTC/ETH/SOL long-short):**
  - Report the 2022 short-side P&L separately.
  - Compare against a multi-lookback ensemble (T1) for parameter robustness.
  - Report correlation with a daily Donchian ensemble.
  - Include funding drag on shorts, which was often negative in 2022 and therefore paid shorts.

### Gaps
- No crypto-specific CTA index or fund letter with strategy-level 2022 returns (trend vs market-neutral) was retrievable.
- The full Pythagoras article is paywalled.
- The 2022 split of crypto trend performance in Man AHL's or Concretum's backtests was not found.

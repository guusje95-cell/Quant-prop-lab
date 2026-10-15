# Intraday and Short-Horizon Systematic Strategies in Gold, Silver, Crude Oil and FX Majors (2015-2026 literature scan)

Scope note: this scan used about 20 search calls. Full-text fetching was blocked in this environment (WebFetch DNS failure; curl got proxy 403). All findings below therefore come from abstracts, repository records and secondary summaries returned by search. Exact Sharpe ratios and coefficient tables were mostly not visible, and the Gaps sections list them. Nothing below is invented. Where I give a candidate test rule, it is my own translation of a cited mechanism into a testable spec and is labelled as an inference.

Testing context: Dukascopy 1-min bid/ask CFD data 2013-2026 (XAU, XAG, WTI, Brent, NG, Cu, Bund, T-bond, ~13 FX pairs) plus CME 1-min futures (GC, SI, CL, 6E, 6J, ZN). Target: net Sharpe >= 0.8, small daily losses, low correlation to long-only daily crypto trend. Already rejected here: daily multi-asset CFD trend, daily breakouts/sweeps, rolling-hedge pairs stat-arb.

---

## Q1. Gold: intraday seasonality (Asia/overnight vs London/NY), London fix effects, macro-announcement reaction

### Takeaway
The best-documented gold effect is "positive overnight / negative daytime" (peer-reviewed, 1985-2012), plus a practitioner/thesis "hat-shaped" pattern: gold rises in Asian hours and falls through London/NY. Fix-based edges (Caminschi & Heaney 2014) depended on information leaking during the old telephone fix. That edge was very likely structurally removed by the 2015 move to the electronic LBMA auction and is not tradable now. I found no peer-reviewed post-2015 out-of-sample test of the session effect net of costs. It is cheap to test on our data and is the top gold candidate.

### Cited Findings
- **Overnight vs day returns in gold.** Using COMEX gold futures, London Fix spot, gold miners and gold funds (1985-2012), overnight returns are significantly positive and day returns significantly negative. The authors suggest the gold price is "(too) high at the opening" of the various markets. Venue: Journal of Economics and Finance (Springer, 2017; DOI 10.1007/s12197-017-9403-0). — [Springer](https://link.springer.com/article/10.1007/s12197-017-9403-0); [ResearchGate](https://www.researchgate.net/publication/318356821_Overnight_versus_day_returns_in_gold_and_gold_related_assets)
- **Hat-shaped intraday seasonality.** A Copenhagen Business School MSc thesis (May 2019) finds gold "appreciating during eastern trading hours in a robust way and depreciating for the rest of the day." It attributes this to Chinese and Indian demand and possibly to fix manipulation. The thesis also cites prior evidence of significant changes in volume, volatility and returns in the 30 minutes before the London fixing. It is a student thesis, not peer-reviewed. — [CBS thesis PDF](https://research.cbs.dk/files/59803241/651553_Thesis_Contract_13383.pdf)
- **Practitioner version.** Practitioner blogs attribute a "down into the London PM fix" tendency to Dimitri Speck (seasonal-chart vendor) and claim it has persisted for decades. No primary data is cited, and other practitioners dismiss the fix as a non-driver. Treat these claims as unverified. — [Copi-tools blog](https://copi-tools.com/blog/xauusd-anomaly/); [Marketstalkers](https://marketstalkers.co.uk/blog/posts/market-profile-on-gold-futures-gc); [Forexr](https://forexr.com/learn/lbma-gold-price-and-london-fix)
- **Recent blog check (ETF, US session only).** A 2025-era blog backtest of gold ETFs finds most gains accrue close-to-open, with intraday (US cash session) returns near zero. Not peer-reviewed. — [Quantified Strategies substack](https://quantifiedstrategies.substack.com/p/a-quantitative-look-at-the-gold-overnight)
- **Caution on overnight-drift backtests.** Quantpedia (Vojtko & Dujava) found GDX's apparent overnight drift of more than 30% p.a. "diminished significantly" when execution was moved to 9:31 using 1-min data. Lesson: OHLC open prices overstate overnight edges, so use 1-min bid/ask fills. — [Quantpedia](https://quantpedia.com/dangers-of-relying-on-ohlc-prices-the-case-of-overnight-drift-in-gdx-etf/)
- **China night-session evidence.** The introduction of night trading in Chinese gold/silver futures changed intraday predictive patterns, and both intraday momentum and reversal are significant there. Venue: Global Finance Journal vol. 64 (2025). — [IDEAS](https://ideas.repec.org/a/eee/glofin/v64y2025ics1044028325000110.html); [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1044028325000110)
- **London PM gold fix leak (Caminschi & Heaney, "Fixing a Leaky Fixing", Journal of Futures Markets 34(11), 2014, DOI 10.1002/fut.21636).**
  - Instruments: GC futures and GLD.
  - Volume and volatility rose sharply right after the fixing start, before the result was published.
  - There were statistically significant returns in the 4 minutes after the fixing start for informed traders.
  - Early-fix trades predicted the fix direction, "in some cases exceeding 90%". A forum summary gives about 70% after the call starts and about 80% within 5 minutes.
  - No significant returns after the result was published.
  - Context: Barclays was fined US$44m, Deutsche Bank exited the fixings, and the silver fix was replaced by an electronic auction (LBMA Silver Price).
  - Sources: [IDEAS](https://ideas.repec.org/a/wly/jfutmk/v34y2014i11p1003-1039.html); [UWA repository PDF](https://api.research-repository.uwa.edu.au/ws/files/4725264/A0205_use_this.pdf); [UWA news](https://www.news.uwa.edu.au/201410067021/research/uwa-research-finds-gold-and-silver-price-setting-open-exploitation)
- **Gold vs US macro announcements (Elder, Miao & Ramchander, Journal of Banking & Finance 2011; 2002-2008 intraday data).**
  - Gold, silver and copper futures react quickly to surprises.
  - 8:30 ET releases, especially payrolls, have the largest impact.
  - Positive US surprises push gold and silver down and copper up.
  - Source: [Mountain Scholar record](https://mountainscholar.org/handle/10217/206884)
- **Practitioner NFP studies (FXStreet, 2021-2023).** The correlation of the gold move with the NFP surprise was about -0.48 at 15 minutes, about -0.3 at 1 hour and near 0 at 4 hours, and the authors say these correlations were not statistically significant. Their reading is that the initial reaction partly fades within hours, but this is not significant evidence of a tradable reversal. — [FXStreet](https://www.fxstreet.com/analysis/us-march-nonfarm-payrolls-preview-analyzing-golds-reaction-to-nfp-surprises-202203310915)

### Inferences
- **G1 candidate: gold session-seasonality (highest-priority gold test).**
  - Rule: long XAUUSD from about 22:00/23:00 UTC (Asia open, after the CME daily break) to about 07:00 UTC (London open), flat otherwise.
  - Variant: also short from London open to NY close.
  - Execution: use 1-min bid/ask.
  - Costs: at a 2-3 bp spread, one round trip per day is about 5-7.5 bp/day per leg pair. The edge must exceed about 13-19% p.a. of gross drift, which is plausible only in strong gold years. The 2013-2026 sample includes gold's 2013-2015 bear market, a useful stress test.
  - Correlation: likely low with crypto trend, because it is a gold-specific flow effect. However, long-only overnight gold carries gold beta, which in 2024-2026 co-moved somewhat with crypto risk-on/debasement narratives.
  - Prop fit: the short leg can hedge beta. A long-Asia/short-London pair is near beta-neutral over a day and should have small daily losses.
- **G2: London fix trading.** The pre-2015 leak edge is very likely dead. The LBMA Gold Price became an electronic IBA auction in March 2015 (from my own knowledge, not verified in this scan). Only a test for a "drift into 15:00 London PM auction then reversal" remains, and the evidence for it is practitioner-only.
- **G3: macro-surprise response.** Directional rules need a consensus-surprise dataset that is not in our data list. A surprise-free alternative is a fade/continue test of the first 5-15 min move after 8:30 ET NFP/CPI. Evidence for either direction is weak.
- Because 2013-2015 microstructure differs (pre-auction fix), split the gold test into 2013-2015 and 2015-2026.

### Gaps
- Neither the Springer paper's effect sizes or Sharpe nor the CBS thesis's numbers were retrieved (full text blocked).
- No peer-reviewed post-2015 replication of the Asia-up / London-NY-down gold pattern was found, and no cost-adjusted Sharpe exists in any source found.
- No study measuring post-announcement drift vs reversal in gold futures after 2011 was found.
- Speck's original data and the CBS "manipulation" claim are unverified.

---

## Q2. FX: time-of-day/session effects, WM/Reuters 4pm fix reversal, month-end rebalancing, announcement drift, short-term reversal

### Takeaway
The strongest and most recent evidence is Krohn, Mueller & Whelan (Journal of Finance 2024). Across the top 9 currencies over 21 years, the USD appreciates into the major FX fixes and depreciates afterward, producing a W-shaped 24h pattern that is "pervasive and highly statistically significant". The mechanism is dealer inventory risk. This is the most promising FX time-of-day family for our data. Supporting evidence:
- Breedon & Ranaldo find currencies depreciate during their home trading hours.
- Melvin & Prins (2015) document month-end hedging flows at the 4pm fix.

Evidence on a short reversal right after the WMR 4pm fix says it disappeared after the 2015 widening of the fix window to 5 minutes. Do not prioritise that one.

### Cited Findings
- **Krohn, Mueller & Whelan, "Foreign Exchange Fixings and Returns around the Clock", Journal of Finance 79(1):541-578, 2024, DOI 10.1111/jofi.13306.**
  - The USD appreciates in the run-up to FX fixes and depreciates afterward, tracing a W-shaped return pattern around the clock.
  - Reversals across the top 9 currencies over 21 years are "pervasive and highly statistically significant", worth more than US$1bn/day based on spot volumes.
  - Natural experiments indicate the published reference rate sets the timing.
  - Proposed mechanism: dealers intermediate unconditional USD demand at fixes and bear inventory risk.
  - The working-paper version (Bank of Canada SWP 2021-48) says futures order imbalances are not related to the reversals.
  - A replication package (code and data) exists.
  - Sources: [Warwick WRAP](https://wrap.warwick.ac.uk/id/eprint/177333); [BoC SWP 2021-48](https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf); [AEA 2020 draft](https://benny.aeaweb.org/conference/2020/preliminary/paper/2dedYfDH); [BoC supporting info](https://oar-rao.bank-banque-canada.ca/record/711)
- **Related work on dealer hedging ahead of fixings.** A catalogue entry says dealer hedging ahead of fixings drives intraday reversals in both OTC and exchange-traded markets. — [TU Freiberg catalogue](https://katalog.ub.tu-freiberg.de/Record/0-1775558460/Description)
- **Breedon & Ranaldo, "Intraday Patterns in FX Returns and Order Flow" (SNB WP 2011-04; QMUL WP 694, 2012; later published in the Journal of Money, Credit and Banking 2013 per my knowledge).**
  - Currencies tend to depreciate during their local trading hours, and this is confirmed across a range of currencies.
  - For EURUSD it forms "a simple, profitable trading strategy".
  - Mechanism: participants are net buyers of foreign currency during their own hours. The same pattern appears in order flow, corroborated by single-market-maker data.
  - Sample: 10 years of high-frequency data.
  - Sources: [SNB WP](https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04); [QMUL](https://qmul.ac.uk/sef/research/workingpapers/2012/items/694.html)
- **WMR 4pm fix microstructure.**
  - Evans, O'Neill, Rime & Saakvitne, "Fixing the Fix? Assessing the Effectiveness of the 4pm Fix", FCA Occasional Paper 46 (Oct 2018). After the fix window was lengthened to 5 min in 2015, benchmark efficiency improved, but tracking error, quoted spreads and price impact rose, and HFTs traded more aggressively during the fix. — [FCA OP46](https://www.fca.org.uk/publication/occasional-papers/occasional-paper-46.pdf)
  - A secondary summary (fx-markets) says short-term reversals around the 4pm fix declined after the 2013 rigging reports and disappeared completely after 2015. — [fx-markets](https://www.fx-markets.com/node/3864546)
  - Marsh, Panagiotou & Payne (2017) found a small price reversal in the minute after the 4pm fix that is not seen at other fixing points, and inter-dealer order flow at the fix is uninformative for returns. — [Panagiotou, Norges Bank](https://www.norges-bank.no/contentassets/619c8b75e1ed4ba691e8ad6a006855e6/39-panagiotou---the-wmr-fix-and-its-impact-on-currency-markets-.pdf); [EFMA 2017](https://www.efmaefm.org/0efmameetings/efma%20annual%20meetings/2017-athens/phd/The%20WMR%20Fix%20and%20its%20Impact%20on%20Currency%20Markets%20-%20Panagiotou.pdf)
  - Saakvitne (2016) models "banging the close" as optimal execution. — [Saakvitne PDF](https://c.mql5.com/forextsd/forum/174/banging_the_close_-_fix_orders_and_price_manipulation.pdf)
- **Month-end hedging flows (Melvin & Prins, "Equity hedging and exchange rates at the London 4 p.m. fix", Journal of Financial Markets 22:50-72, 2015).**
  - Most international equity managers hedge FX at the 4pm fix and adjust hedges mainly at the month-end fix.
  - Foreign equity appreciation over the month predicts depreciation of that foreign currency before the month-end fix. Example: if the S&P outperforms, foreign holders of US equities must sell more USD forward, which weakens the USD into the fix.
  - Sources: [ECB workshop version](https://ecb.eu/events/pdf/conferences/131216/Third_FX_Workshop_MELVIN_PRINS_Equity%20hedging%20and%20exchange%20rates%20Nov%202013.pdf); practitioner explanation at [investingLive](https://investinglive.com/Education/!/how-month-end-rebalancing-works-20191128); bank flow models such as [BNY iFlow](https://www.bny.com/corporate/global/en/solutions/platforms/execution-services/iflow/investor-trends/july-rebalancing-favor-gbp-sell-usd.html)
- **Intraday momentum in FX (Elaut, Frömmel & Lampaert, "Intraday momentum in FX markets: Disentangling informed trading from liquidity provision", Journal of Financial Markets 37:35-51, 2018, DOI 10.1016/j.finmar.2016.09.002).** A citing paper reports the result as the first half-hour return predicting the last half-hour return in the RUB-USD market (Moscow exchange). It is not on G10 majors. — [IDEAS](https://ideas.repec.org/a/eee/finmar/v37y2018icp35-51.html); citing summary in [Hull repository](https://hull-repository.worktribe.com/OutputFile/3303156)
- **FOMC and the USD.**
  - Mueller, Tahbaz-Salehi & Vedolin ("Exchange Rates and Monetary Policy Uncertainty", Journal of Finance 2017): a short-USD / long-other-currencies strategy earns significantly larger excess returns on FOMC days, larger for high interest-differential currencies. The attribution is from the paper's file name and my knowledge, since the search page did not show the authors. — [Columbia-hosted PDF](https://drupalgsb-test.paas.cc.columbia.edu/sites/default/files-efs/pubfiles/15021/Exchange%20Rates%20andMonetary%20Policy%20Uncertainty_June2016.pdf)
  - Karnaukh: the USD appreciates in the 2 days before Fed hikes and depreciates before cuts, predictable from fed funds futures. — [Karnaukh PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0019/190315/DollarAheadFOMC_NinaKarnaukh.pdf); [Macrosynergy](https://macrosynergy.com/?p=41075)
  - Lee & Wang: post-FOMC returns cancel about 65% of the positive pre-FOMC drift. — [Georgia Tech essays](https://repository.gatech.edu/entities/publication/3187038d-e40b-4817-9213-36f536d67588)
- **Short-term reversal in FX.** 1-min EURUSD shows mean reversion (Wiśniewska, Folia Oeconomica Stetinensia 2015), but costs are not addressed. — [reference-global](https://reference-global.com/article/10.1515/foli-2015-0014)
- **Liquidity vs information effects in EURUSD.** Liquidity effects in the EUR/USD limit order book last 2-10 minutes, while information effects are permanent (Bank of Canada WP 08-44). This implies pure liquidity reversals are too short and small to beat a 0.5-1 bp spread. — [BoC WP 08-44](https://oar-rao.bank-banque-canada.ca/record/1501/files/wp08-44.pdf)

### Inferences
- **F1 candidate: fix-timed USD W-pattern (top FX test).**
  - Rule: short USD vs a basket (EUR, JPY, GBP, AUD, CHF, CAD, NZD...) from a fix (Tokyo about 00:55 UTC, ECB 13:15 CET-ish, WMR 16:00 London) for several hours after it.
  - Mirror leg: long USD in the hours leading into each fix.
  - Timing: fix times must be DST-aware.
  - Costs: with 0.5-1 bp EURUSD and worse on crosses (JPY, AUD about 1 bp, others 1.5-3 bp), expect costs of 2-6 bp/day for 2-4 round trips. The paper's magnitudes were not retrieved, so viability is unknown until tested.
  - Signal: an average-of-basket signal improves the signal-to-noise ratio, and in practice it is a short-USD-after-fix / long-USD-into-fix overlay.
  - Correlation: likely near-zero with crypto trend, because it is a dealer-inventory flow effect.
- **F2 candidate: Breedon-Ranaldo local-hours depreciation.** Rule: short EUR in European hours / long EUR in US hours, and short JPY in Tokyo hours. This overlaps heavily with F1, so test them jointly.
- **F3 candidate: month-end hedge rebalancing (Melvin-Prins).**
  - Signal: on the last business day, compute the month-to-date return of the S&P 500 minus foreign equity indices (needs equity data such as SPX/STOXX/Nikkei/FTSE closes, which we can source).
  - If US equities outperformed, short USD into the 16:00 London month-end fix, entering about 1-3 hours before (or from the prior day) and exiting at the fix.
  - Only 12 trades/yr, so the Sharpe of a stand-alone version will be noisy. It is best as an overlay.
  - Caveat: this is widely known and publicised by bank flow models (BNY iFlow, etc.), so decay is likely.
- **F4: the 1-minute post-4pm reversal** is likely dead post-2015 (fx-markets/FCA) and below a CFD spread anyway. Reject a priori.
- **F5: FOMC-day short USD / pre-FOMC drift.** Only 8 events/yr. It can be an add-on. The pre-FOMC drift (Karnaukh) needs fed funds futures data.
- Generic FX intraday reversal at 1-5 min horizons is liquidity-driven (2-10 min half-life) and will not survive 0.5-1 bp CFD spreads plus slippage. It needs spreads below what CFD brokers charge.

### Gaps
- Krohn et al. bp/day magnitudes, per-currency results, trading-strategy Sharpe and post-2015 subsample were not retrieved. The JF reproducibility package should be downloaded for exact fix times and magnitudes.
- Breedon-Ranaldo EURUSD strategy performance and costs were not retrieved.
- Melvin-Prins effect size (bp per 1% equity outperformance) and post-2015 persistence were not found.
- The Elaut et al. G10/EURUSD applicability is unknown, since the evidence found is RUB-USD only.
- I found no independent post-publication replication of Krohn et al.

---

## Q3. Crude oil: intraday momentum, EIA inventory announcement effects, settlement-time effects

### Takeaway
The crude evidence is thinner and partly ETF-based:
- Intraday momentum: the first half-hour, including the overnight move, predicts the last half-hour (USO ETF).
- On EIA Wednesdays, the 10:00-10:30/10:30-11:00 ET half-hour predicts the last half-hour (Wen, Indriawan, Lien & Xu, Energy Journal 2023).
- Around EIA releases, prices react within minutes and revert quickly. There is informed pre-release trading of about -0.25% ahead of positive inventory surprises (Rousse & Sévi).
- Natural gas storage reports show a pre-announcement drift that is profitable after costs (Energy Economics). This matters because NG is in our dataset.

### Cited Findings
- **Wen, Indriawan, Lien & Xu (2023), "Intraday Return Predictability in the Crude Oil Market: The Role of EIA Inventory Announcements", The Energy Journal 44(5).**
  - On EIA days (Wed 10:30 ET), the third half-hour return significantly and positively predicts the last half-hour return.
  - On non-EIA days, only the first half-hour predicts, and that predictability comes mainly from the overnight return.
  - Attributed to informed trading and thinner liquidity around the release.
  - Sources: [IDEAS](https://ideas.repec.org/a/aen/journl/ej44-5-xu.html); [IAEE exec summary](https://www.iaee.org/ej/ejexec/ej44-5-Xu-exsum.pdf); [Adelaide repository](https://digital.library.adelaide.edu.au/items/13d367dd-06b2-4eca-8d21-4dfeb46c4f55)
- **Wen, Cho, Ma & Xu (USO ETF).** The first half-hour return, measured from the previous close, predicts the last half-hour in- and out-of-sample. It is stronger in crises and on high realized-volatility, high-volume, high-overnight-return and jump days. — [MPRA 97134](https://ideas.repec.org/p/pra/mprapa/97134.html)
- **Rousse & Sévi (Energy Journal).**
  - On days with inventory surprises, there is buyer-initiated order imbalance in the 2 hours before the release.
  - There is an average price drop of -0.25% ahead of positive (bearish) surprises.
  - There is an overreaction that partly reverses in the hours after.
  - Sources: [IAEE exec summary](https://iaee.org/ej/ejexec/EJ40-2_Rousse_ExecSum.pdf); [SAGE](https://journals.sagepub.com/doi/10.5547/01956574.42.2.mpro)
- **Journal of Energy Markets.** WTI price, volatility and volume respond within minutes to inventory shocks, with effects lasting about 25 min and prices reverting quickly. Some participants may get the news about 10 minutes early. — [Risk.net](https://www.risk.net/journal-of-energy-markets/5728636/an-analysis-of-intraday-market-response-to-crude-oil-inventory-shocks)
- **Journal of Futures Markets (WTI, Brent and INE tick data).** EIA announcements significantly affect intraday returns, and liquidity to a lesser extent. — [MetaTOC listing](https://metatoc.com/papers/119762-intraday-liquidity-in-international-crude-oil-futures-markets-news-impacts-commonality-and-spillovers)
- **Natural gas analogue (Energy Economics).** About half of the storage-report-day return occurs before the release, and a simple intraday strategy is profitable after costs. This comes from a search summary; the exact citation was not retrieved. — summary in search results alongside [IAEE](https://www.iaee.org/ej/ejexec/ej44-5-Xu-exsum.pdf) (see Gaps)
- **Market-level intraday momentum (Baltussen, Da, Lammers & Martens, "Hedging Demand and Market Intraday Momentum", Journal of Financial Economics 142(1):377-403, 2021).** Across 60+ futures (equities, bonds, commodities, currencies, 1974-2020), the return over the rest of the day positively predicts the last-30-minute return. The effect reverts over the next days and is linked to gamma hedging by option market makers and leveraged ETFs. — [SSRN 3760365](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365); [IDEAS](https://ideas.repec.org/a/eee/jfinec/v142y2021i1p377-403.html); [Erasmus](https://pure.eur.nl/en/publications/hedging-demand-and-market-intraday-momentum/)
- **Settlement time.** I found no source specific to crude settlement time (14:28-14:30 ET). The Baltussen et al. last-30-min result is the closest, and for CL "close" means pit settlement.

### Inferences
- **O1 candidate: CL/WTI EIA-day intraday momentum.**
  - Rule: on EIA Wednesdays, take sign(return 10:30-11:00 ET), or 10:00-10:30 per the "third half-hour" counting from the 9:00 open. Trade in that direction from 14:00 to 14:30 ET (settlement).
  - Non-EIA days: use sign(previous 14:30 settlement to 9:30 ET).
  - Costs: the WTI CFD spread is about 3-5 cents (about 4-8 bp at $60-80 crude) per round trip. A 30-min hold with an average absolute return of maybe 30-50 bp makes costs material but not prohibitive. Use CL futures data for the cleaner test.
  - Expected frequency: daily, giving about 250 trades/yr.
- **O2: NG pre-storage-report drift.** NG CFD spreads are wide, so check the size of the edge first.
- **O3: fade the EIA reaction** (quick reversion within about 25 min per the JEM paper). This needs tight execution, and the CFD spread plus slippage at 10:30 ET may eat it.
- Correlation: oil intraday-momentum returns should be close to zero-correlated with daily crypto trend. Exception: crisis days, where both intraday momentum and trend may profit.

### Gaps
- No Sharpe, return or cost numbers were retrieved for either Wen et al. paper.
- No crude settlement-time study was found.
- The exact author/title of the Energy Economics NG pre-announcement paper was not retrieved.
- No post-publication replication of the crude intraday momentum was found.

---

## Q4. Cross-asset intraday momentum (Gao-Han-Li-Zhou style) applied to commodities/FX; Li-Sakkas-Urquhart ITSM

### Takeaway
Intraday time-series momentum is broadly documented:
- Baltussen et al. (JFE 2021) find it in 60+ futures, including commodities and FX.
- Li, Sakkas & Urquhart (JFM 2022) find it in 16 developed equity markets.
- Chinese commodity futures show it (Jin et al., JFM 2020).

However, the strongest out-of-sample test in the literature (Rosa, JFM 2022) finds that predictability "disappears in the out-of-sample period" for the overnight-to-last-half-hour signal, apart from threshold/strong-signal regimes. A 2026 falsification study on MNQ found nothing net of costs. Expect weak post-publication performance. Use strong-signal thresholds and test on GC/CL/6E futures sessions.

### Cited Findings
- **Gao, Han, Li & Zhou, "Market Intraday Momentum" (Journal of Financial Economics 2018).**
  - Data: SPY 1993-2013.
  - The first half-hour return (from the prior close) predicts the last half-hour.
  - Stronger on volatile, high-volume, recession and macro-news days.
  - Holds for 10 other ETFs and 2 international index futures.
  - Sources: [paper PDF](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf); [Alpha Architect](https://alphaarchitect.com/2014/08/attention-prop-traders-the-first-half-hour-of-trading-predicts-the-last-half-hour/)
- **Li, Sakkas & Urquhart, "Intraday Time Series Momentum: Global Evidence and Links to Market Characteristics" (Journal of Financial Markets 57, 2022).**
  - 16 developed markets. ITSM is significant in- and out-of-sample in most.
  - Stronger with low liquidity, high volatility and discrete information.
  - The sample is equity indices; commodities and FX were not confirmed.
  - Sources: [Reading accepted version](https://reading-9.eprints-hosting.org/95566/1/Accepted-Version.pdf); [Nottingham repository](https://nottingham-repository.worktribe.com/output/5273197)
- **Jin, Kearney, Li & Yang, "Intraday time-series momentum: Evidence from China" (Journal of Futures Markets 2020, DOI 10.1002/fut.22084).** In copper, steel, soybean and soybean meal futures, the first half-hour predicts the last half-hour in all 4. The effect is stronger in metals on high-volume/volatility sessions, and the strategy beats always-long and buy-and-hold. — [Hull repository](https://hull-repository.worktribe.com/output/3295550)
- **Chinese metal futures after night trading.** The day-session first half-hour lost predictive power after night trading was introduced, and the night-session first half-hour became the effective predictor. This shows the signal depends on session structure. — [Pacific-Basin Finance Journal 80 (2023), IDEAS](https://ideas.repec.org/a/eee/pacfin/v80y2023ics0927538x2300152x.html)
- **Baltussen, Da, Lammers & Martens (JFE 2021).** Market intraday momentum (rest-of-day predicts last 30 min) is found across 60+ futures in equities, bonds, commodities and currencies, 1974-2020. Mechanism: gamma hedging. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365)
- **A replication summary of a similar test** reports "two instruments of four have the right sign, with no t above 0.61, and no R² above 0.06%", with strategies ranging from −0.90% to +2.45%/yr. The snippet was truncated, so the instruments are unclear. — [Harbourfront Quant substack](https://harbourfrontquant.substack.com/p/market-intraday-momentum-and-hedging)
- **Rosa, "Understanding intraday momentum strategies" (Journal of Futures Markets 42(12):2218-2234, 2022).** The overnight to last-half-hour predictability disappears out of sample. A Markov-switching model shows two regimes, and a threshold strategy beats always-active. — [IDEAS](https://ideas.repec.org/a/wly/jfutmk/v42y2022i12p2218-2234.html); [Wiley](https://onlinelibrary.wiley.com/doi/10.1002/fut.22375)
- **2026 arXiv falsification (MNQ futures).** None of 14 OHLCV intraday-momentum signal families met the criteria after round-trip friction. — [arXiv 2605.04004](https://arxiv.org/pdf/2605.04004)
- **End-of-day reversal at the stock level** (Baltussen, Da & Soebhag, EFMA 2024) is the opposite sign to market-level momentum. — [EFMA PDF](http://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2024-Lisbon/papers/EndofDayReversal_withnames.pdf)

### Inferences
- **X1 candidate: multi-asset intraday momentum, thresholded.**
  - Rule: for GC, SI, CL, 6E, 6J and ZN on CME RTH-equivalent sessions, signal = return from prior settlement to settlement minus 30 min.
  - Trade in that direction over the last 30 min, only if |signal| > k × trailing σ (Rosa's threshold finding). Equal-risk weight across assets.
  - FX caveat: for 24h FX, "close" is ill-defined. Use the CME settlement of 6E/6J (14:00 CT) or the WMR 4pm fix as the session end. The Krohn et al. fix-reversal logic may clash with momentum into the 4pm fix, so test both directions.
  - Costs: one round trip/day. For a 30-min hold, typical absolute moves of about 10-20 bp on gold/FX against a 2-3 bp gold or 0.5-1 bp EURUSD spread are workable only with a high hit rate. Given Rosa's OOS failure, assign a low prior.
- Diversification: intraday momentum strategies are long-gamma-like and tend to earn on high-volatility/crisis days. That likely gives low or even negative correlation with long-only crypto trend in normal times, but possible co-movement in crash days, when crypto trend is flat or short-filtered.

### Gaps
- Baltussen et al. per-asset results for gold, crude and FX futures, and their Sharpe, were not retrieved.
- Whether Li-Sakkas-Urquhart cover commodities/FX was not confirmed.
- The Hull paper's 4 commodity markets were not confirmed to include gold.

---

## Q5. Correlation with crypto trend; which need spreads tighter than CFD brokers offer; carry

### Takeaway
The flow- and time-of-day-driven effects should be close to uncorrelated with a long-only daily crypto trend book, because their P&L comes from dealer inventory or hedging flows, not from directional risk-on beta. These are the FX fix W-pattern, month-end hedging, gold session seasonality and oil EIA-day momentum. Effects that live at 1-10 minute horizons cannot survive CFD spreads. These are the post-4pm-fix reversal, EIA-release fade, liquidity reversals and the pre-2015 gold fix leak. FX carry (daily) was not researched in this scan, beyond the FOMC-day carry evidence.

### Cited Findings
- EURUSD liquidity-driven price effects last only 2-10 min. — [BoC WP 08-44](https://oar-rao.bank-banque-canada.ca/record/1501/files/wp08-44.pdf)
- The post-4pm-fix reversal was small (about 1 minute) pre-2015 and gone after 2015. — [Panagiotou](https://www.norges-bank.no/contentassets/619c8b75e1ed4ba691e8ad6a006855e6/39-panagiotou---the-wmr-fix-and-its-impact-on-currency-markets-.pdf); [fx-markets](https://www.fx-markets.com/node/3864546)
- WTI EIA reaction reverts within about 25 min, and some participants get the news about 10 min early. — [Risk.net JEM](https://www.risk.net/journal-of-energy-markets/5728636/an-analysis-of-intraday-market-response-to-crude-oil-inventory-shocks)
- After the 2015 fix-window change, quoted spreads and price impact around the WMR fix increased, so trading at the fix itself costs more. — [FCA OP46](https://www.fca.org.uk/publication/occasional-papers/occasional-paper-46.pdf)
- FX short-USD returns are concentrated on FOMC days and are larger for high-carry currencies. — [Columbia-hosted PDF](https://drupalgsb-test.paas.cc.columbia.edu/sites/default/files-efs/pubfiles/15021/Exchange%20Rates%20andMonetary%20Policy%20Uncertainty_June2016.pdf)

### Inferences
- **Priority test list for Dukascopy/CME 1-min data, ranked by evidence quality × post-2015 plausibility × cost-viability:**
  1. **F1 Krohn et al. fix W-pattern** (FX basket, multi-hour holds, 2-4 trades/day). Strongest recent top-journal evidence. Hold horizon is hours, so a 0.5-1.5 bp spread is plausibly affordable. Uncorrelated mechanism.
  2. **G1 gold Asia-long / London-NY-short.** Peer-reviewed day/night evidence plus a thesis. One to two trades/day at 2-3 bp. Uncorrelated mechanism, but watch gold beta.
  3. **O1 CL EIA-day + overnight-signal intraday momentum** (last half-hour). Moderate evidence, one trade/day.
  4. **F3 Melvin-Prins month-end hedge flow.** Low frequency, overlay only.
  5. **X1 thresholded multi-asset intraday momentum.** Weak OOS (Rosa), low prior.
  6. **F5 FOMC-day short-USD / carry tilt.** Very low frequency.
- **Reject a priori because the edge is smaller than CFD spreads or structurally dead:**
  - 1-min post-4pm-fix reversal
  - Old gold/silver telephone-fix leak
  - Tick/minute FX liquidity reversals
  - Fading the first minutes of the EIA reaction (also latency-dependent)
- Daily-loss profile: all priority candidates are intraday or flat overnight (except G1's overnight hold, which is an Asia-session hold on a 24h market). Single-trade risk can be capped with per-trade stops, which is compatible with a 3-5% daily loss limit at modest leverage.
- Multiple-testing caution: session, fix and threshold choices create many degrees of freedom. Pre-register exact fix times (DST-aware), the cost model (bid/ask fills), and a 2013-2019 / 2020-2026 split.

### Gaps
- No FX carry or short-term (daily/weekly) FX reversal papers from 2015-2026 were retrieved in this scan, so the carry part of the brief is under-covered.
- No source quantified correlation between any of these strategies and crypto trend. That must be measured empirically.
- No study reports CFD-broker (vs interbank or futures) net performance for any of these effects.

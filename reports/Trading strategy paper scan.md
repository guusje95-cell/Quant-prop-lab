# Flow-timed intraday trades beat published factor zoos

Only a handful of 2018-2026 strategies justify backtest time against the target of net Sharpe ≥ 0.8, low correlation to long-only daily crypto trend, a smooth equity curve and prop-firm loss limits. All of them earn from **when** flows hit a market (dealer inventory around FX fixes and the European equity open, gold's Asia/London split, crude's EIA day, intraday trend bursts in BTC). None of them predicts **which** asset wins over days. In the literature the cross-sectional crypto factors, positioning signals (funding, OI, long/short ratios) and taker-flow signals are either cost-dominated or failed point-in-time replication. The scan also confirms that the project's earlier rejections were correct. The independent out-of-sample evidence on the Zarattini noise-area breakout (SPY Sharpe 0.39 for May 2024 to March 2026, near zero since 2025 on ES) shows US index intraday momentum decaying in the 0DTE era. The project's US100 Sharpe of 0.71 at 1 bp is therefore close to a ceiling, not a floor. The best new leads are:

| Data set | Lead | Evidence base |
|---|---|---|
| Databento | Conditional European-open long in ES | Two 2023 top-journal papers; Sharpe about 1.6 reported net |
| Dukascopy | Krohn-Mueller-Whelan USD fix "W" pattern | JF 2024, replication package available |
| Dukascopy | Gold Asia-long / London-NY-short | Peer-reviewed day/night split |
| Binance | Long-short intraday BTC/ETH trend | Concretum 2026; about 1.6 gross Sharpe, no net figure |

A realistic planning haircut is 50% on any published Sharpe with no independent replication, and the published out-of-sample number wherever one exists. With 6 years of crypto data, even a true Sharpe of 0.8 only reaches t ≈ 2, so Binance tests need tighter pre-registration than the 13-year Dukascopy tests. One caveat applies throughout: the research notes were built from abstracts and search excerpts, because full-text fetches were blocked. Several exact parameters and net-of-cost tables are therefore unknown and are marked as such.

## Seven rejections and one decay already line up with the evidence

The project's own rejections closely match what independent researchers found, and that agreement should anchor the priors used below.

**Cross-sectional momentum and reversal.** These failed on 58 perps in the project. Externally, a pre-registered practitioner audit found 1-day cross-sectional reversal on the top 20 coins at Sharpe **-1.41 after costs** and 7-day momentum at -0.03 ([GitHub mtrinkner](https://github.com/mtrinkner/crypto-funding)). Large-cap crypto momentum suffers crashes of about **-255% in a single month** from one coin's jump in the short leg ([Springer](https://link.springer.com/article/10.1007/s11408-025-00474-9)). Daily reversal lives in illiquid coins, while the largest coins show daily momentum instead ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1057521921002349)).

**Chi et al. basis factor and funding contrarian.** The cross-sectional funding "crowding" signal had an in-sample IC of +0.06 that fell to **+0.0001 point-in-time**. The net book lost 78.9% a year ([GitHub mtrinkner](https://github.com/mtrinkner/crypto-funding)). An SSRN post-mortem on Binance perps "compels rejection" of OHLCV and funding cross-sectional alpha at 8 hours ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6701738)).

**Gao 2018 half-hour momentum.** This came out at -1.06 on US500 in the project. The strongest out-of-sample test finds overnight-to-last-half-hour predictability "disappears in the out-of-sample period" ([Wiley](https://onlinelibrary.wiley.com/doi/10.1002/fut.22375)). A 2026 falsification study on MNQ found none of 14 OHLCV intraday-momentum families survived friction ([arXiv](https://arxiv.org/pdf/2605.04004)). A re-test on 1,085 SPX sessions since April 2022 gives a slope of +0.006 (t = 0.6) ([dev.to/FirmTape](https://dev.to/firmtape/intraday-momentum-is-dead-in-the-0dte-era-we-measured-it-on-1085-spx-sessions-43g0)).

**Futures trend+carry (F7/F9).** The decay from about 1.5 to 0.8 is industry-wide. SG Trend's 2022 return of about +27% hides an otherwise flat decade ([Ryan O'Connell Finance](https://ryanoconnellfinance.com/managed-futures-cta/)). The index then fell **20.4% from May 2024 to May 2025** ([Cambridge Associates](https://www.cambridgeassociates.com/insight/does-trend-followings-recent-struggle-signal-that-the-strategy-is-structurally-broken/)). That drawdown falls after the project's data ends in 2024-03, so the 0.70 HOLDOUT figure is optimistic.

**Noise-area breakout.** The project's own number is US100 0.71 at 1 bp and 1.12 at 0.3 bp. It sits right where independent evidence lands. The paper reports SPY Sharpe 1.33 net for 2007-2024 ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172)). A dedicated out-of-sample paper finds **0.39 for May 2024 to March 2026** ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7290621)). A frozen-protocol replication on SPY and ES finds Sharpe near zero since 2025 ([GitHub codecat-ops](https://github.com/codecat-ops/zarattini-2024-momentum-spy)). QuantConnect users report 0.7-0.8 on NQ/QQQ ([QuantConnect](https://www.quantconnect.com/forum/discussion/15192)). The cost sensitivity (0.71 to 1.12 for a 0.7 bp change) means fill quality, not signal design, decides this strategy.

**BTC 21-23 UTC window.** The source sample is Gemini data to February 2022 ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4081000)). Only 2022-2026 is genuinely out of sample for the project. A follow-up summary reports a rough 2022-2023 ([PapersWithBacktest](https://paperswithbacktest.com/blog/bitcoin-never-sleeps-exploiting-seasonality)).

## Haircuts: halve published Sharpe, then demand t above 3

The decay literature gives a consistent central estimate. McLean and Pontiff find predictor returns **26% lower out of sample and 58% lower after publication** across 97 predictors, and in-sample stars decay most ([JF PDF](https://Www.Gwern.net/doc/economics/2016-mclean.pdf)). Falck, Rej and Thesmar find 72 strategies keep **about 50%** of in-sample performance, and publication year alone explains about 30% of the variation in decay ([RePEc](https://ideas.repec.org/p/arx/papers/2105.01380.html)). Harvey and Liu caution that a flat 50% is "a serious mistake": marginal Sharpe ratios deserve much more than 50% and strong ones less. They also give a multiple-testing method that converts Sharpe to a p-value adjusted for the number of trials ([Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF)). Harvey, Liu and Zhu argue new factors need t > 3 ([NBER](https://www.nber.org/papers/w20592)). In crypto specifically, cross-sectional results swing widely with researcher design choices, a new "factor zoo" ([IRFA 2024](https://www.sciencedirect.com/science/article/abs/pii/S1057521924000383)).

Turning this into rules gives the following tiers:

| Evidence tier | Planning Sharpe = | Example |
|---|---|---|
| Independent OOS exists | the OOS number, not the paper's | Noise-area SPY: 0.39, not 1.33 |
| Peer-reviewed, cost-aware, no replication | 0.5 × published net | Bondarenko-Muravyev 1.6 → 0.8 |
| Gross-only or authors' own vendor research | 0.4 × gross, then subtract the in-house cost model | Concretum BTC 1.6 gross → about 0.6 before costs |
| Vendor/practitioner/unrefereed | 0.25 × claim, or ignore | Turn-of-candle 4.96; Aperiodic "about 2.5" |
| Lab-searched variants | Harvey-Liu with N = ledger configurations | Any sweep beyond the pre-registered rule |

Sample length matters as much as the haircut. The t-statistic of an annualised Sharpe is roughly SR × √years. On 6 years of Binance data (2020-2026), a true 0.8 strategy shows t ≈ 2.0, and t = 3 requires an observed Sharpe of about 1.2. On 13 years of Dukascopy data, Sharpe 0.8 gives t ≈ 2.9. The practical rule is to require a backtest Sharpe of about **1.5 or more at realistic costs** before a published crypto strategy can be expected to deliver 0.8 live. FX, gold and index strategies on 2013-2026 data can pass at a lower in-sample bar.

Costs deserve their own haircut. A practitioner saw a crypto backtest Sharpe of 13.4 vanish after adding fees ([DEV](https://dev.to/pavel_kkkkazantsev/my-crypto-backtest-had-a-sharpe-of-134-then-i-added-trading-costs-5718)). Quantpedia showed that GDX's apparent overnight drift of more than 30% a year "diminished significantly" once fills moved from OHLC opens to 1-minute prices ([Quantpedia](https://quantpedia.com/dangers-of-relying-on-ohlc-prices-the-case-of-overnight-drift-in-gdx-etf/)). Every test below therefore fills at the next 1-minute bar using bid/ask (Dukascopy) or tick-plus-commission (Databento). Binance taker fills use about 5 bp per side, and each test also reports a 2× cost stress.

## Ranked candidates by data set

### Databento CME: the European-open dealer-inventory trade leads

**C1. Conditional overnight drift in ES (priority 1 overall).** Bondarenko and Muravyev show that the 4 hours around the European open earn the **entire** E-mini S&P return. The window is roughly 23:30-03:30 ET, and the reported Sharpe of about 1.6 "remains high after transaction costs" ([RePEc](https://ideas.repec.org/a/cup/jfinqa/v58y2023i3p939-967_1.html); [Alpha Architect](https://alphaarchitect.com/market-return-around-the-clock/)). Boyarchenko, Larsen and Whelan tie the drift to order imbalance at the previous US close, which points to dealer inventory risk. They also find that **selloffs reverse more strongly than rallies** ([NY Fed SR917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf); [RePEc](https://ideas.repec.org/p/fip/fednsr/87539.html)).

The counter-evidence is that bid-ask spreads flipped the unconditional overnight return negative in one implementation ([CXO](https://www.cxoadvisory.com/?p=33743)). That may explain the project's failed Liu & Tse and euro-open CFD tests, since overnight CFD spreads are wide. ES's 0.25-point tick costs roughly 0.5 bp, so the futures test is the fair one. The **conditional** version (trade only after a down close) uses the published asymmetry to raise the edge per trade.

No post-2023 out-of-sample test exists. Expected correlation with crypto trend is low, because the trade is in ES for 1-4 hours. It is long equity beta, though, and crash days hurt both books. For prop fit, the trade is inside the CME session day (17:00-16:00 CT), so it is intraday under a session-day definition. Each firm's rules must be checked. Planning Sharpe is about 0.8 at 50% haircut on the unconditional version.

**C2. Noise-area breakout on NQ/ES (priority 2, conditional retest only).** The full-sample run adds little, because the decay is established. The useful test is whether a **volatility-conditioned** version survives 2024-2026. Baltussen et al.'s hedging-demand intraday momentum is stronger on high-volatility, large-move days ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365)). In the post-2022 SPX sample it survives only when dealers are short gamma (slope +0.055, t = 3.1, unverified blog analysis) ([dev.to/FirmTape](https://dev.to/firmtape/intraday-momentum-is-dead-in-the-0dte-era-we-measured-it-on-1085-spx-sessions-43g0)). The prop fit is ideal: flat by close, long-short and close to zero beta. Intraday momentum earns on trending crash days, which gives favourable tail correlation with crypto trend.

**C3. Crude EIA-day intraday momentum (priority 3).** Wen, Indriawan, Lien and Xu find that on EIA Wednesdays the half-hour containing the 10:30 ET release positively predicts the last half-hour. On other days only the first half-hour (mostly the overnight move) predicts ([IDEAS](https://ideas.repec.org/a/aen/journl/ej44-5-xu.html); [IAEE summary](https://www.iaee.org/ej/ejexec/ej44-5-Xu-exsum.pdf)). A USO study reports the overnight-plus-first-half-hour signal holds out of sample and is stronger in crises and on high-volatility and jump days ([MPRA](https://ideas.repec.org/p/pra/mprapa/97134.html)). No Sharpe, cost figure or post-publication replication was retrieved. Its mechanism (informed trading around inventory news) is unrelated to crypto.

**C4. Thresholded multi-asset last-30-minute momentum (priority 4).** Baltussen et al. document the effect in more than 60 futures from 1974 to 2020. Secondary summaries put asset-class Sharpe at 0.87-1.73 ([Harbourfront](https://harbourfrontquant.substack.com/p/market-intraday-momentum-and-hedging)). Rosa's out-of-sample failure leaves only the strong-signal regime ([Wiley](https://onlinelibrary.wiley.com/doi/10.1002/fut.22375)). A diversified GC/SI/CL/6E/6J/ZN book is the cheapest way to see whether anything outside US equities survived the 0DTE era. The prior is low.

**C5. 5-minute ORB on NQ (priority 5, one shot).** Zarattini and Aziz report a hit rate of about 24% and +0.13R per trade on QQQ, with commissions only and no out-of-sample period. A costed replication on five index CFDs found "gross reproduced, net zero" ([MQL5](https://www.mql5.com/en/blogs/post/776235)). NQ futures costs are small relative to the opening range, so NQ is the only venue worth one pre-registered run. The 24% hit rate means long losing streaks, which caps risk per trade at about 0.5% under a 3-5% daily limit.

**C6. Reduced trend+carry (deferred).** Planning Sharpe is about 0.5-0.6 gross after the decay already in the data. It requires overnight holding, and index-level drawdowns of about 20% do not fit 4-6% trailing prop limits. Run it only if an overnight-permitted account is in scope. Basis-momentum ([Boons & Prado](https://4nations.albertjmenkveld.com/papers/boonsprado17.pdf)) and commodity skewness ([Quantpedia](https://quantpedia.com/strategies/skewness-effect-in-commodities)) are pre-2015-sample add-ons for that book only.

### Dukascopy CFD: FX fixes and gold sessions are the only high-quality leads

**D1. USD fix "W" pattern (priority 1 for Dukascopy).** Krohn, Mueller and Whelan show that the dollar **appreciates into the major FX fixes and depreciates afterwards** across the top 9 currencies over 21 years. The effect is "pervasive and highly statistically significant". Natural experiments show the published reference rate sets the timing, and dealer inventory risk is the mechanism. A replication package exists ([Warwick WRAP](https://wrap.warwick.ac.uk/id/eprint/177333); [BoC SWP 2021-48](https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf)).

Breedon and Ranaldo's finding that currencies depreciate during their home trading hours, "a simple, profitable trading strategy" for EURUSD, overlaps closely and should be tested jointly ([SNB](https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04)). The magnitudes in bp/day and any post-2015 subsample were not retrieved, so cost viability at 0.5-3 bp spreads is the open question. Download the replication package first. The holds last hours, so costs are plausibly affordable. The flow is dealer-intermediated USD demand, so correlation with crypto trend should be close to zero. With 2-4 intraday round trips a day and basket diversification, this is the smoothest candidate in the scan.

**D2. Gold Asia-long / London-NY-short (priority 2).** Gold futures, the London fix, miners and gold funds show **significantly positive overnight and negative daytime returns, 1985-2012** ([Springer](https://link.springer.com/article/10.1007/s12197-017-9403-0)). A CBS thesis finds gold rises in eastern hours "in a robust way" and falls the rest of the day ([CBS](https://research.cbs.dk/files/59803241/651553_Thesis_Contract_13383.pdf)). No post-2015 cost-adjusted test was found. The long-Asia/short-London pair is near beta-neutral over a day, which removes gold's 2024-2026 debasement-trade co-movement with crypto. Split the sample at March 2015 because the fix moved to an electronic auction then. The pre-2015 fix-leak edge documented by Caminschi and Heaney is very likely gone ([IDEAS](https://ideas.repec.org/a/wly/jfutmk/v34y2014i11p1003-1039.html)).

**D3. Noise-area breakout on DAX, FTSE and Nikkei CFDs (priority 3).** Li, Sakkas and Urquhart find intraday time-series momentum significant in and out of sample in most of 16 developed markets. It is stronger with low liquidity, high volatility and discrete news ([Reading](https://reading-9.eprints-hosting.org/95566/1/Accepted-Version.pdf)). Those markets have less 0DTE dealer-gamma flow than the US. The idea that their momentum decayed less is a hypothesis, not a finding, but it is the main untested direction in the CFD set. Keep US100 as a cost-sensitivity control.

**D4. Melvin-Prins month-end hedge rebalancing (priority 4, overlay).** Equity managers adjust FX hedges at the month-end 4pm fix. Foreign-equity outperformance therefore predicts the foreign currency weakening into that fix ([ECB workshop version](https://ecb.eu/events/pdf/conferences/131216/Third_FX_Workshop_MELVIN_PRINS_Equity%20hedging%20and%20exchange%20rates%20Nov%202013.pdf)). Bank flow models publicise it widely ([BNY iFlow](https://www.bny.com/corporate/global/en/solutions/platforms/execution-services/iflow/investor-trends/july-rebalancing-favor-gbp-sell-usd.html)), so decay is likely. With 12 trades a year it can only be an overlay on D1.

**D5. FOMC-day short USD (overlay, low priority).** Short-USD returns concentrate on FOMC days and are larger in high-carry currencies ([Columbia PDF](https://drupalgsb-test.paas.cc.columbia.edu/sites/default/files-efs/pubfiles/15021/Exchange%20Rates%20andMonetary%20Policy%20Uncertainty_June2016.pdf)). At 8 events a year it lacks statistical power on its own.

### Binance USD-M: one intraday-trend lead and one cross-sectional holdout

**B1. Long-short intraday BTC/ETH trend (priority 1 for Binance).** Zarattini, Pagani and Barbon report that an ensemble of high-frequency intraday trend models on BTC earns **about 1.6 Sharpe gross** over 2018-2025. Vol-targeted long-only BTC earns just below 0.8. Strength concentrates from Sunday 19:00 New York for about 24 hours (the Monday Asian open) and is stronger after mid-2020 ([Concretum](https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/)). No net figures and no independent replication exist. The authors also wrote the noise-area paper that decayed on SPY, which argues for the strict tier-3 haircut.

The structural case is still the best on Binance. The strategy is long-short and intraday, unlike daily crypto trend. Intraday momentum is "especially profitable during market downturns" in related BTC work ([Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/fire.12290)), which gives a hedge-like profile against long-only trend. At about 1 round trip a day and roughly 10 bp taker cost, it needs about 25% a year of gross edge to clear costs. Test BTC and ETH only first.

**B2. Overnight-vs-US-hours BTC window, beta-neutralised (priority 2).** This is the general form of the 21-23 UTC candidate. On NYSE-open days most BTC return accrues outside NYSE hours ([Quantpedia](https://quantpedia.com/are-there-seasonal-intraday-or-overnight-anomalies-in-bitcoin/)). A 2018-2023 5-minute study finds overnight returns of about +0.093% against -0.029% during US trading hours ([CCN](https://www.ccn.com/news/crypto/bitcoins-overnight-crypto-unlock-new-insights-equity-volatility/)). Across 38 exchanges, returns are lowest at roughly 01:00-05:00 UTC ([Springer](https://link.springer.com/article/10.1007/s11156-024-01304-1)).

The weakness is regime dependence. The premium is strongest in speculative periods and fades in bear markets ([Aalto](https://aaltodoc.aalto.fi/items/e4962f5a-045a-4131-b329-cc27926f6c4f)). Its losing regime therefore coincides with crypto trend's. The test has to show that a **long-short** version (long the strong window, short 01:00-05:00 UTC) removes enough beta to diversify. It also has to show that 21-23 UTC is not just the best-looking slice of the broader window. The existing note that 21-23 needs maker fills stands. At taker costs, a 2-hour hold carries about 10 bp round trip against hourly mean returns of a few bp.

**B3. CTREND on 20 perps, weekly (priority 3).** Fieberg et al. combine price and volume trend signals across horizons with machine learning on more than 3,000 coins. The factor is not subsumed by known factors, survives costs and "persists in big, liquid coins", out of sample from April 2016 to May 2022 ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4601972)). Reported figures are about 1.89-2.44% per week for a top-100 build, and a $1 price filter cuts the median Sharpe from 1.64 to 1.13. The evaluation ends May 2022, so **June 2022 to 2026 on Binance perps is a genuine holdout**. That is rare and valuable.

The risks are the small universe (20 names gives low breadth) and the 2022-2023 failure of crypto momentum strategies in general ([Springer](https://link.springer.com/chapter/10.1007/978-981-95-2566-9_30)). It is market-neutral and weekly, so expected correlation with long-only trend is near zero. Single-coin short squeezes are the tail risk, so cap per-name weight.

**B4. Cascade reversal via OI flush (priority 4, overlay).** Perp drawdowns are about a third the size of quarterly-futures drawdowns and **mean-revert quickly**, and liquidations have limited price impact ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5036933)). No paper offers a tradable post-cascade rule, and early-warning precursors are event-specific ([arXiv](https://arxiv.org/pdf/2607.27070)). Binance no longer serves historical liquidation snapshots, so the 5-minute OI drop is the proxy. Events are rare and cluster across coins, so this is an exploratory overlay. It buys exactly when trend followers exit.

**B5. Quarter-hour opening imbalance, 4-12h (priority 5, single shot).** Kim and Hansen find that opening order imbalance at :00/:15/:30/:45 on six Binance perps forecasts 4-12 hour returns over 2021-2024. That result is **in-sample only**. The out-of-sample claim covers just the 10-second opening return ([arXiv](https://arxiv.org/abs/2607.09426); [Pith](https://pith.science/paper/2607.09426)). A rebuild from every Binance trade since 2023 is titled "Real Pattern, No Trade" ([Microstructure Lab](https://themicrostructurelab.substack.com/p/the-quarter-hour-clock-in-crypto)). It is worth exactly one frozen rule on post-October-2024 data.

**B6. Positioning risk overlay (not standalone).** Crypto carry is highest when trend-chasing leverage demand is high, and it coincides with margin spikes and liquidations in drawdowns ([BIS](https://www.bis.org/publ/work1087.htm)). The plausible use of the funding, premium and OI data is therefore to **scale down the existing trend book** when both are extreme. This is untested anywhere and must be pre-registered as a risk test, judged on drawdown and Calmar rather than Sharpe.

### Candidate summary

| # | Strategy | Source | Reported | Independent / post-pub evidence | Planning Sharpe | Exp. corr. to crypto trend | Rank |
|---|---|---|---|---|---|---|---|
| C1 | ES European-open, conditional on down close | Bondarenko-Muravyev JFQA 2023; Boyarchenko et al. RFS 2023 | about 1.6, net of costs | none post-2023; CXO notes spreads can flip it | about 0.8 | low; positive in crashes | 1 |
| D1 | USD fix W-pattern basket | Krohn-Mueller-Whelan JF 2024 | "highly significant"; Sharpe not retrieved | none found; replication package available | unknown; test | about 0 | 2 |
| B1 | BTC/ETH long-short intraday trend | Concretum 2026 | about 1.6 gross | none | about 0.6 before costs | low; hedge-like in crashes | 3 |
| D2 | Gold Asia-long/London-short | J. Econ. Finance 2017; CBS 2019 | significant, 1985-2012 | none post-2015 | unknown | about 0 (pair) | 4 |
| C2 | NQ/ES noise-area, vol-conditioned | Zarattini et al. 2024; Baltussen et al. JFE 2021 | 1.33 net (SPY) | OOS 0.39; about 0 since 2025 | 0.3-0.6 | about 0 | 5 |
| B3 | CTREND on 20 perps | Fieberg et al. JFQA 2025 | median 1.13-1.64 | none after May 2022 | about 0.5 | about 0 | 6 |
| D3 | DAX/FTSE/Nikkei noise-area | Li-Sakkas-Urquhart JFM 2022 (mechanism) | ITSM significant OOS | pre-0DTE only | unknown | about 0 | 7 |
| C3 | CL EIA-day momentum | Wen et al. Energy J. 2023 | significant; no Sharpe | none | unknown | about 0 | 8 |
| B2 | BTC overnight window, long-short | Quantpedia; Xiamen; Padysak-Vojtko | about 1.58 (21-23, unverified) | 2022-23 drawdown | about 0.4 | positive regime overlap | 9 |
| C4 | Multi-asset last-30m, thresholded | Baltussen et al. JFE 2021; Rosa 2022 | 0.87-1.73 (secondary) | OOS failure except strong-signal regime | about 0.3 | negative in tails | 10 |
| B4 | OI-flush cascade reversal | Gornall et al. 2025 (mechanism) | no rule published | none | unknown | timing-negative | 11 |
| B5 | Quarter-hour imbalance | Kim-Hansen 2026 | in-sample only | practitioner: "no trade" | about 0 | about 0 | 12 |
| D4/D5 | Month-end hedge; FOMC short USD | Melvin-Prins 2015; Mueller et al. JF 2017 | significant | widely publicised | overlay | about 0 | overlay |

The correlation column is inference from strategy structure and regime findings. **No source in the scan measured correlation with a crypto trend book**, so it must be computed in-house from daily P&L. The one regime anchor is BTC-S&P correlation: about 0.09 on average before 2020, peaking at 0.65 in March 2020 ([21Shares](https://www.21shares.com/it/insights/newsletter-issue-72)), and around 0.3 on a 5-year average ([Spark](https://www.spark.money/tools/bitcoin-correlation-calculator)). Any equity-beta sleeve (C1, long-only B2) will correlate most on exactly the days that hurt.

## Over twenty strategies to drop before spending compute

The drop list falls into four groups.

**Cost-dominated.** The edge per trade is smaller than a realistic round trip. Taker-flow reversal on Binance shows real predictability, but the gross edge is **about 1.3 bp against about 5 bp** round-trip cost ([Pith](https://pith.science/paper/2608.21888)). The bar-to-bar imbalance lags add nothing over lagged signs. One-minute FX liquidity reversals last only 2-10 minutes ([BoC WP 08-44](https://oar-rao.bank-banque-canada.ca/record/1501/files/wp08-44.pdf)). The fade of the first minutes of the EIA reaction is latency-dependent, with some participants seeing the news about 10 minutes early ([Risk.net](https://www.risk.net/journal-of-energy-markets/5728636/an-analysis-of-intraday-market-response-to-crude-oil-inventory-shocks)). Cross-venue funding dispersion earns 3.69 Sharpe gross but 0.39 net, and -0.36 in 2025-26 ([GitHub mtrinkner](https://github.com/mtrinkner/crypto-funding)). ORB on index CFDs nets to zero ([MQL5](https://www.mql5.com/en/blogs/post/776235)).

**Structurally dead.** Post-4pm-fix reversals disappeared after the 2015 window change ([fx-markets](https://www.fx-markets.com/node/3864546)). The gold telephone-fix leak ended with the auction ([IDEAS](https://ideas.repec.org/a/wly/jfutmk/v34y2014i11p1003-1039.html)). The pre-FOMC equity drift essentially vanished after 2015 ([Kurov et al.](https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf)). Unconditional US intraday momentum and the Gao variant are covered in the first section. Crypto carry fell from Sharpe 6.45 (2020-2025) to **negative in 2025** ([arXiv](https://arxiv.org/pdf/2510.14435)). The best risk-engineered switching version decays to 0.13 in 2025-26 and needs spot legs the data set lacks ([GitHub mtrinkner](https://github.com/mtrinkner/crypto-funding)).

**Not robust or not replicated.** Crypto day-of-week, Monday, weekend and turn-of-month effects fail Mueller's 2024 test. Only lower weekend activity is robust ([RePEc](https://ideas.repec.org/a/eee/finlet/v64y2024ics1544612324004598.html)). Turn-of-candle's Sharpe 4.96 comes from one exchange's 2021 simulation ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10015199/)). VPIN predicts BTC jumps, not direction ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0275531925004192)). Long/short-ratio contrarian rules have no academic test at all ([cryptorank](https://cryptorank.io/news/feed/4f469-bitcoin-perpetual-futures-long-short-ratios-binance-okx-bybit)). VWAP trend's reported figures were far above public replications, one of which shows live Sharpe -0.6 ([QuantConnect](https://www.quantconnect.com/reports/2dd44a5c1394e0ba3de9c7f4d7dc0716)). Daily RSI(2) on SPX returned 1.7% a year over 2016-2026 ([Backtrex](https://backtrex.com/en/backtests/connors-rsi-2-sp-500)). OPEX week turned negative or noisy after 2021 ([Schaeffer's](https://www.schaeffersresearch.com/content/analysis/2023/03/08/caution-potentially-volatile-week-ahead)).

**Redundant or out of scope.** Shen-Urquhart-Wang BTC half-hour momentum is mechanically the rejected Gao rule ([Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/fire.12290)). Directional time-series funding/OI timing on BTC is short when trend is long, which repeats the rejected contrarian test. Premium-extreme directional trades are the same trade on a faster clock. LTW size is degenerate on 20 large coins ([NBER](https://www.nber.org/papers/w25882)). Stocks-in-Play ORB (Sharpe 2.81 reported, about 2.4 replicated) needs a 7,000-stock intraday universe the project does not hold ([QuantConnect](https://www.quantconnect.com/forum/discussion/18444)). It is the strongest replicated result in the scan, and the only one excluded purely on data grounds.

## Pre-registered test queue

The protocol is common to every test, and each test is logged in the append-only ledger before its first run. One frozen rule per candidate is run, plus at most two named robustness variants. Any further variant counts toward Harvey-Liu N.

**Fills and costs:**

| Data set | Fill | Cost assumption | Stress |
|---|---|---|---|
| Dukascopy | next 1-minute bar's bid/ask | spread as quoted | 1.5× spread |
| Databento | next 1-minute bar | 1 tick plus $2.5/side per contract | 2 ticks |
| Binance | next 1-minute bar | 5 bp/side taker | 10 bp/side |

Funding is applied to Binance positions held across 00/08/16 UTC. Sizing is volatility-targeted to 10% annualised per sleeve, with a hard stop that caps any single day at 1% of equity.

**Splits:**

| Data set | Train | Test | Holdout |
|---|---|---|---|
| Dukascopy | 2013-2019 | 2020-2023 | 2024-2026 |
| Databento | to 2019 | 2020-2023 | 2024-2026 |
| Binance | 2020-2022 | 2023-2024 | 2025-2026 |

CTREND is an exception: its holdout starts June 2022.

**Pass criteria:** net Sharpe ≥ 0.8 in test and ≥ 0.5 in holdout, Harvey-Liu-adjusted t ≥ 2.5, worst day ≥ -1.5% at target vol, and daily P&L correlation with the crypto trend book ≤ 0.2, including on that book's 20 worst days.

### Databento (CME)

| Order | ID | Pre-registered rule | Key robustness variant |
|---|---|---|---|
| 1 | C1 | ES: if the RTH close (16:00 ET) is below the prior RTH close, buy at 02:00 ET and exit at 03:30 ET. Otherwise flat. | Unconditional 23:30-03:30 ET window |
| 2 | C2 | NQ and ES: band = today's RTH open × (1 ± mean of \|close/open − 1\| at the same minute over 14 days). Check at :00/:30. Long above the upper band, short below the lower band. Trailing stop = max(band, VWAP) for longs and min(band, VWAP) for shorts. Flat at 15:59 ET. Report 2024-2026 separately. | Trade only when VIX or 20-day realised vol is above its 1-year median |
| 3 | C3 | CL: on EIA days, take the sign of the 10:30-11:00 ET return and hold that direction 14:00-14:30 ET. On other days, take the sign of the prior 14:30 settle → 09:30 ET return and hold over the same window. | EIA days only |
| 4 | C4 | GC, SI, CL, 6E, 6J, ZN: signal = settle(t-1) → settle(t) − 30 min. Trade its sign into the settlement only if \|signal\| > 1 × trailing 60-day σ of the signal. Equal risk. | Threshold 0.5σ |
| 5 | C5 | NQ: the first 5-minute RTH bar sets direction. Enter at bar 2's open. Stop at the opposite side of bar 1, target 10R or 15:59 ET. Risk 0.5% per trade. | None |

### Dukascopy (CFD)

| Order | ID | Pre-registered rule | Key robustness variant |
|---|---|---|---|
| 1 | D1 | Equal-weight basket of EUR, GBP, JPY, AUD, CHF, CAD and NZD vs USD. Long USD from 2h before to the WMR 16:00 London fix, then short USD from the fix to +3h. Same for the Tokyo 09:55 JST fix. DST-aware. Exact windows are taken from the Krohn et al. replication package before any run. | Add the ECB reference-rate fix (time from the replication package) |
| 2 | D2 | XAUUSD: long 23:00-07:00 UTC, short 07:00-16:00 UTC, otherwise flat. Report 2013-02/2015 and 03/2015-2026 separately. | Long leg only |
| 3 | D3 | Apply the C2 rule on DAX, FTSE 100 and Nikkei 225 CFDs with each index's cash open/close, plus US100 as a control. | Volatility filter as in C2 |
| 4 | D4 | Overlay on D1: on the last business day, if the S&P 500 month-to-date return exceeds that of an equal-weighted STOXX 600/FTSE/Nikkei basket, short USD from 13:00 to 16:00 London. Reverse the trade if the S&P lagged. | None |

### Binance USD-M

| Order | ID | Pre-registered rule | Key robustness variant |
|---|---|---|---|
| 1 | B1 | BTC and ETH: apply the C2 rule with session open 00:00 UTC, 14-day same-minute band, checks at :00/:30, VWAP trailing stop and flat at 23:59 UTC. Taker cost 5 bp/side. Separate Sunday 23:00 UTC-Monday 23:00 UTC P&L. | Session open 23:00 UTC Sunday-anchored weekly |
| 2 | B2 | BTC: long 21:00-23:00 UTC, short 01:00-05:00 UTC (equal notional), taker fills. | Long 20:00 → 13:30 UTC, short 13:30 → 20:00 on NYSE days |
| 3 | B3 | 20 perps, point-in-time listing: weekly (Monday 00:00 UTC) cross-sectional elastic-net combination of 1/5/20/60/120-day MA price and volume ratios, trained expanding-window on data to May 2022 and frozen. Rank-weighted long-short, max 15% per name, beta-neutral to BTC. | Equal-weight top/bottom tercile |
| 4 | B4 | Per coin: if the 1h return < -3σ (30-day hourly σ), the 1h OI change < -5%, and 1h volume > the 95th percentile, go long at the next 5-minute bar. Stop at the cascade low − 1 ATR, exit at 12h. Mirror for squeezes. | Hold 4h / 24h |
| 5 | B5 | BTC, ETH, SOL, XRP, DOGE, ADA: take the sign of (2·takerBuy − vol)/vol in the 00:00 UTC opening minute and hold 8h. Data from November 2024 onward only. | None |
| 6 | B6 | Overlay on the existing trend book: halve exposure when both the 30-day z-score of the premium index and the z-score of the 7-day OI change exceed the 95th percentile, and restore at the 80th. Judge on max drawdown and Calmar, not Sharpe. | None |

## Conclusion

The pattern across all five note sets is that edges with a **named counterparty constraint** survive best. Examples are dealers carrying inventory overnight or across a fix, hedgers forced to a benchmark time, and option dealers short gamma. Edges defined only by a price or positioning characteristic (funding, momentum ranks, taker ratios) have collapsed once tested point-in-time with costs. That favours Dukascopy FX/gold and Databento ES as the likeliest sources of a diversifying sleeve this cycle. Binance's contribution is more likely to be the B6 risk overlay on the existing trend book than a new standalone alpha. B1 is the exception, and only if its net Sharpe clears about 1.5 in-sample.

The binding constraint is no longer finding papers. It is statistical power and cost realism. The project should therefore spend its next effort on three things: pulling the Krohn et al. replication package, building a tick-accurate ES overnight cost model, and computing correlations against the crypto trend book on stress days only. Each of those determines more of the final answer than any additional literature search.

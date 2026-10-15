# Futures Trend/Carry Performance 2015-2026, Enhancements, Publication Decay, and Prop-Firm Implementability

Scope note: ~20 tool calls. Several primary hosts (cfm.com, arxiv.org, cambridgeassociates.com, toptradersunplugged.com) failed DNS from this sandbox, so a number of figures come from search-result extracts of those pages, not full-page reads. They are flagged where relevant. Items marked "[training memory, unverified]" are from prior knowledge and need checking before they are cited.

Project context (given): the 155-futures trend+carry (F7/F9) had VAL 0.63, TEST 0.96, HOLDOUT 0.70, and decayed from ~1.5 Sharpe (pre-2010) to ~0.8 (post-2010). Data ends 2024-03.

## Q1. Net Sharpe of diversified futures trend and carry 2015-2026; 2022; 2023-2025

### Takeaway
Industry trend (SG CTA / SG Trend) has been roughly flat to mildly positive since 2015, apart from one exceptional year. 2022 was the best year in the index's history (SG CTA +20.1%, SG Trend about +27%). 2023 was flat to -3%, 2024 was +2.4% (SG CTA), and May 2024 to May 2025 brought a -20.4% SG Trend drawdown, the second largest since 2000. 2025 ended about +2.4% (SG Trend) after a -10% first half. A realistic net Sharpe for 2015-2025 at the index level is low, roughly 0.2-0.4 (my inference, not a published number). That is well below the 1.0+ gross figures in the academic papers. Your 0.7-0.8 post-2010 project Sharpe is gross of fees and above what the industry realised.

### Cited Findings
- SG CTA Index 2022: +20.1%, its best calendar year since SocGen began calculating the index in 2000. One report gives +20.2%. — [Hedgeweek](https://hedgeweek.com/news/trend-followers-turn-leaders-ctas-deliver-record-returns-2022)
- SG Trend Index 2022: about +27%, while the S&P 500 fell 18% and the US Aggregate bond index fell about 13%. — [Ryan O'Connell Finance (secondary)](https://ryanoconnellfinance.com/managed-futures-cta/)
- SG CTA 2023: StoneX reports the benchmark lost "almost 3%". Quantpedia describes the year as "flat". — [StoneX](https://www.stonex.com/en/insights/ctas-on-course-for-positive-january-returns/); [Quantpedia](https://quantpedia.com/exploration-of-cta-momentum-strategies-using-etfs/)
- SG CTA 2024: about +2.4% ("close to flat despite the good start to the year"). — [CFM, "Steady Trends: the reality of CTA return dispersion"](https://www.cfm.com/steady-trends-the-reality-of-cta-return-dispersion/) (search extract only; page unreachable)
- SG Trend Index 2025 path: -9.3% YTD by April (April alone -4.9%), -10.03% YTD in July, and a full-year finish of about +2.39%. — [TTU April 2025](https://www.toptradersunplugged.com/trend-following-performance-report-april-2025/); [TTU July 2025](https://www.toptradersunplugged.com/trend-following-performance-report-july-2025/); [TTU Dec 2025](https://www.toptradersunplugged.com/trend-following-performance-report-december-2025/); [Wisdom Trading](https://wisdomtrading.com/insights/if-your-trend-system-has-been-struggling-youre-not-alone-heres-whats-going-on/)
- Another tracker reports the SG CTA Index (a different series from SG Trend) at about -0.2% YTD for 2025. — [Aussie Turtles](https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2025/)
- The SG Trend Index fell 20.4% from May 2024 to May 2025, its second-largest drawdown since 2000. Its since-inception maximum drawdown is about 20.6%. Cambridge Associates asks whether trend is "structurally broken" (conclusion not retrieved). — [Cambridge Associates](https://www.cambridgeassociates.com/insight/does-trend-followings-recent-struggle-signal-that-the-strategy-is-structurally-broken/) (search extract)
- CTA return dispersion is large. SocGen's 2025 CTA update discusses YTD dispersion among constituents. — [SG CTA Update 2025](https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025)
- Dispersion example: AQR Managed Futures Full Vol returned +5.5% in H1 2025, +9.3% in September 2025, and was in the "mid- to high-teens" YTD by early October 2025. AQR Helix (alternative-market trend) returned about +18% in 2024 and +7.4% in H1 2025. These are press reports. — [Hedgeweek](https://www.hedgeweek.com/aqr-outpaces-trend-following-peers-with-double-digit-h1-gains/); [Institutional Investor](https://www.institutionalinvestor.com/article/aqrs-big-year-funds-climb-stock-picks-and-macro-moves)
- Simplify Managed Futures ETF (ticker CTA): +9.55% (2022), -2.23% (2023), +24.15% (2024), +0.88% (2025). This is a single trend+carry-ish fund, not an index. — [financecharts](https://www.financecharts.com/etfs/CTA/performance)
- Academic baselines:
  - Trends Everywhere (Babu, Levine, Ooi, Pedersen, Stamelos, JOIM 2020) reports a gross Sharpe of 1.17 for 12-month TSMOM on traditional assets. It extends TSMOM to 82 new markets (alternative markets) and 16 equity long-short factors, and finds trend worked across them. — [AQR Trends Everywhere](https://www.aqr.com/Insights/Research/Journal-Article/Trends-Everywhere); [JOIM PDF](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-Trends-Everywhere_JOIM.pdf?sc_lang=en)
  - Hurst, Ooi and Pedersen find TSMOM "consistently profitable" back to 1880. — [Century of Evidence PDF](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf)
- Carry, in-sample (Koijen, Moskowitz, Pedersen, Vrugt):
  - Diversified current-carry Sharpe 1.41 (1980-2011). Commodity carry about 0.50 (0.64 for the carry 1-12 variant). — [Koijen slides](https://www.fmg.ac.uk/sites/default/files/2020-08/Ralph-Koijen-slides.pdf)
  - Published JFE version: average per-asset-class Sharpe about 0.8 and diversified about 1.2. Carry crashes cluster in recessions and liquidity crises (1972-75, 1980-82, Aug 2008-Feb 2009). — [etf.com Swedroe](https://www.etf.com/node/93939.md)
- Carry, other estimates:
  - Baltas multi-asset carry: Sharpe 0.79 with negative skew. Futures carry Jan 1990-Jan 2016: gross Sharpe 0.79-1.04, before rebalancing and leverage costs. — [CXO Advisory](https://cxoadvisory.com/value-premium/carry-trade-across-futures-asset-classes)
- Carry vs trend in 2022: pure trend portfolios materially beat carry-conditioned ones, because the carry filter blocked shorting bonds for most of the year. — [Advisor Perspectives, Feb 2026](https://www.advisorperspectives.com/commentaries/2026/02/26/trend-follow-carry-lessons-bonds-gold-2022)

### Inferences
- Index-level trend since 2015 has been positive mainly because of 2022. Remove 2022 and 2015-2025 is close to zero net of fees. This matches the project's post-2010 decay (1.5 to 0.8). The project's 0.8 is gross and has no 2/20 fee drag, so it is in line with an industry net result of about 0.2-0.4 after roughly 3-4%/yr of fees on 10-15% volatility.
- The project's data ends 2024-03, so it misses the May 2024 to May 2025 trend drawdown (about -20%). A forward-looking HOLDOUT that includes 2024-2025 would very likely come in below 0.70.
- Carry is regime-dependent and fell short when bond trends dominated (2022). Combining carry with trend diversifies but does not stack Sharpe linearly.

### Gaps
- No verified post-2015 Sharpe for the SG Trend or SG CTA index (BarclayHedge page not fetched). Compute it from the BarclayHedge monthly series: [BarclayHedge SG CTA](https://portal.barclayhedge.com/cgi-bin/indices/displayHfIndex.cgi?indexCat=SG-Prime-Services-Indices&indexName=SG-CTA-Index).
- No source found for out-of-sample multi-asset carry Sharpe for 2015-2024.
- Not retrieved:
  - AQR's "You Can't Always Trend When You Want" (Babu et al., JPM 2020). It argues that weak 2009-2019 trend returns came from fewer and smaller trends, not from crowding. That is from training memory and unverified.
  - Updated Hurst-Ooi-Pedersen figures. [training memory, unverified]: the 1880-2013 net-of-2/20 version reports roughly 11% per year, a Sharpe near 1, and positive returns in every decade.
- 2026 YTD SG index performance was not found.

## Q2. Enhancements with out-of-sample support

### Takeaway
Volatility scaling and blending several trend speeds are the best-supported improvements, and they mainly cut risk and tails rather than add alpha. Volatility scaling raises Sharpe meaningfully only for equity and credit (the leverage effect). Carry, basis-momentum and skewness have published cross-sectional support in commodities, mostly on pre-2015 data with little independent out-of-sample evidence. Trend redundancy work (2025) shows that many blended speeds are largely one factor.

### Cited Findings
- Volatility targeting (Harvey, Hoyle, Korgaonkar, Rattray, Sargaison, Van Hemert, Man/Duke):
  - It improves Sharpe only for "risk assets" (equity, credit) through the leverage effect. The effect is small for bonds, FX and commodities.
  - It reduces left-tail events in all asset classes.
  - Equity Sharpe is reported to rise from 0.40 to 0.48-0.51 (secondary summary).
  - It uses a 20-day half-life vol estimate.
  - Sources: [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf); [Alpha Architect](https://alphaarchitect.com/volatility-targeting-improves-risk-adjusted-returns/); [Quantpedia](https://quantpedia.com/the-impact-of-volatility-targeting-on-equities-bonds-commodities-and-currencies)
- Trend speed:
  - TSMOM works across multiple trend horizons in Trends Everywhere. — [AQR](https://www.aqr.com/Insights/Research/Journal-Article/Trends-Everywhere)
  - 2025 papers on CTA replication and trend-premia structure argue that short- and long-term trend factors overlap heavily ("diversification hides redundancy"). — [arXiv 2507.15876](https://arxiv.org/pdf/2507.15876); [arXiv 2510.23150](https://arxiv.org/pdf/2510.23150)
- Trend and carry overlap: the spot-futures basis explains about 36% of TSMOM performance (Finta and Ornelas). — [Imperial thesis / search extract](https://spiral.imperial.ac.uk/entities/publication/da363123-384d-4167-839f-2aa61fdc7826)
- The same Imperial thesis finds carry and momentum out-of-sample returns "highly significant, robust to transaction costs". — [Imperial](https://spiral.imperial.ac.uk/entities/publication/da363123-384d-4167-839f-2aa61fdc7826)
- Basis-momentum (Boons and Prado, JF 2019): outperforms both basis and momentum in predicting commodity spot and term premia. Main tests use 21 commodities (32 in the appendix), and the premium is linked to volatility risk. — [Boons & Prado PDF](https://4nations.albertjmenkveld.com/papers/boonsprado17.pdf)
- Skewness ("Commodities as Lotteries", Fernandez-Perez et al.): buying low-skew and shorting high-skew commodities earns about 8% per year, not explained by backwardation or contango. Quantpedia's backtest covers 1987-2014. — [Quantpedia](https://quantpedia.com/strategies/skewness-effect-in-commodities)
- Intraday momentum (Gao, Han, Li, Zhou, JFE 2018): the first half-hour return of SPY (from the prior close) predicts the last half-hour return (1993-2013). The effect is stronger on volatile days, high-volume days, recession days and macro-news days. The working paper also finds it in two international index futures. — [WUSTL](https://profiles.wustl.edu/en/publications/market-intraday-momentum/); [PDF](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf)
- International intraday TSMOM: economically significant. The US first half-hour also predicts foreign last half-hours. — [Reading accepted version](https://reading-9.eprints-hosting.org/95566/1/Accepted-Version.pdf)
- Concretum "Beat the Market" (Zarattini, Aziz, Barbon, SFI RP 24-97):
  - Mechanism: a "noise area" band built from the 14-day average absolute move from the open to each minute. A breakout triggers a trend position, managed with dynamic trailing stops.
  - Results on SPY, 2007 to early 2024, net of costs: Sharpe 1.33, 19.6% annualised return, 1,985% total.
  - The figures are the authors' own; no independent replication was found.
  - Sources: [SFI](https://www.sfi.ch/fr/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy); [Concretum](https://concretumgroup.com/beat-the-market-an-effective-intraday-momentum-strategy-for-sp500-etf-spy/)

### Inferences
- In this project, volatility scaling should be the default and should not be counted as a source of extra alpha outside equity indices.
- Of the speed-blend gains, expect diversification of path, not more Sharpe.
- Basis-momentum, skew and term-structure slope are worth testing pre-registered on the 155-market panel. Their published samples largely end before 2015, so apply the Q3 haircuts.

### Gaps
- Not found: Baltas & Kosowski specific numbers (volatility estimators, correlation-adjusted TSMOM); commodity seasonality out-of-sample evidence; Levine & Pedersen "Which trend is your friend?" specifics.
- No independent replication of Concretum or Gao et al. after 2015 on ES futures was found.

## Q3. Publication decay and haircuts for backtested Sharpe

### Takeaway
Expect roughly 25-60% decay:
- About 26% from overfitting (McLean-Pontiff out-of-sample, pre-publication).
- About 58% total post-publication (McLean-Pontiff).
- About 50% out of sample (Falck-Rej-Thesmar, 72 strategies).

Harvey-Liu warn that the haircut is nonlinear: marginal Sharpe ratios should be cut by much more than 50%, high ones by less. Hou-Xue-Zhang show that 65% of 452 anomalies fail |t|>1.96 once microcaps are controlled. Practical rule: haircut about 50% by default, more for marginal or heavily searched strategies, and require t > 3.

### Cited Findings
- McLean & Pontiff (JF 2016), 97 predictors: returns are 26% lower out of sample and 58% lower after publication. The 26% is an upper bound on data mining; the remaining roughly 32% is attributed to investors learning from publication. Predictors with higher in-sample returns decay more. — [JF PDF](https://Www.Gwern.net/doc/economics/2016-mclean.pdf); [CFA digest](https://rpc.cfainstitute.org/research/cfa-digest/2016/06/does-academic-research-destroy-stock-return-predictability-digest-summary)
- An earlier working-paper version with 82 characteristics found about 10% out-of-sample and 35% post-publication decay. — [Bocconi WP](https://finance.unibocconi.eu/sites/default/files/files/media/attachments/The%2520Observation%2520Effect%2520%282%2920130502142550.pdf)
- Hou, Xue & Zhang ("Replicating Anomalies", RFS 2020, 452 anomalies):
  - With NYSE breakpoints and value weighting, 65% cannot clear |t|=1.96, and 82% fail a multiple-test hurdle of 2.78.
  - 95 of 102 liquidity anomalies fail.
  - Value, momentum, investment and profitability replicate best.
  - Critics say the result mainly shows anomalies are concentrated in microcaps.
  - Sources: [RePEc](https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2019-2133..html); [Alpha Architect](https://alphaarchitect.com/replicating-anomalies/)
- Harvey, Liu & Zhu (RFS 2016): catalogue 316 factors and argue a new factor needs t > 3.0. They say "most claimed research findings in financial economics are likely false". — [NBER](https://www.nber.org/papers/w20592); [SSRN](https://papers.ssrn.com/abstract=2513152)
- Counterpoint (Jensen-Kelly-Pedersen style / Chen): at least 75% of cross-sectional findings are true, an FDR consistent with the HLZ estimates. — [arXiv 2206.15365](https://arxiv.org/pdf/2206.15365)
- Harvey & Liu "Backtesting" (JPM 2015):
  - A 50% Sharpe haircut is common practice, but "it is a serious mistake to use the rule of thumb 50% haircut". The haircut is nonlinear: high Sharpe ratios are moderately penalised and marginal ones heavily.
  - Method: Sharpe to t-stat, p-value adjusted for the number of tests (Bonferroni/Holm/BHY), then back to Sharpe.
  - The paper provides a profit hurdle, and R code exists.
  - Sources: [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF); [quantstrat R code](https://rdrr.io/github/braverock/quantstrat/src/sandbox/Harvey_Liu_Backtesting/50a170e4e37da951ea1192888418c82a/Haircut_SR%20with%20sample_random_multests.R)
- Falck, Rej & Thesmar ("Why and how systematic strategies decay", 2021; published as "When do systematic strategies decay?", Quantitative Finance 22(11), 2022, pp. 1955-1969):
  - 72 US-equity strategies deliver about 50% of in-sample performance out of sample.
  - Year of publication alone explains about 30% of the cross-sectional variance in Sharpe decay. Overfitting proxies add about 15%; arbitrage-capital proxies add little.
  - Decay is lower in small stocks.
  - Sources: [RePEc/arXiv 2105.01380](https://ideas.repec.org/p/arx/papers/2105.01380.html); [CFM](https://cfm.com/why-and-how-systematic-strategies-decay/); [Evidence Investor](https://www.evidenceinvestor.com/post/why-and-how-systematic-strategies-decay)

### Inferences
Practical haircut rules for this project:
1. The default backtest-to-live Sharpe multiplier is 0.5.
2. For widely published, crowded strategies (12-month TSMOM, carry), the post-2010 realised data in this project already embeds the decay (1.5 to 0.8, about 47%, close to Falck et al.'s 50%). Use the post-2010 or HOLDOUT Sharpe (0.70) as the base and haircut a further 10-25% for fees, slippage and the 2024-25 drawdown not in the data. Planning Sharpe is about 0.5-0.6 gross.
3. New variants found by search within this lab: compute the Harvey-Liu haircut with N = the number of configurations logged in the append-only ledger. A variant with in-sample Sharpe 0.5 over about 15 years has t of about 1.9 and should be discarded.
4. Require t > 3 for new signals.

### Gaps
- The decay papers are all on US equity anomalies. No equivalent decay study for futures/CTA signals was retrieved, so the futures decay rate is inferred from industry index data (Q1).

## Q4. Implementability on ~30 CME futures under prop rules; correlation with crypto trend

### Takeaway
Classic daily or weekly trend and carry need overnight holding. They cannot run on Topstep-style intraday-flat accounts, only on overnight-permitted (often CFD) firms. Even there, 30 markets with micro contracts and tight trailing drawdowns (about 4-6%) are a poor fit for strategies whose index-level drawdowns are about 20%. For intraday-flat rules, the only documented trend analogues are intraday momentum (Gao et al., first half-hour to last half-hour) and opening-range or noise-band breakout (Concretum), both tested mainly on SPY/ES. No published intraday carry exists, since carry accrues over days. No published correlation between SG Trend and crypto trend was found.

### Cited Findings
- Gao et al. intraday momentum: SPY plus ten other ETFs and two international index futures. It fits ES/NQ/YM/RTY flat-by-close rules. — [WUSTL](https://profiles.wustl.edu/en/publications/market-intraday-momentum/)
- Concretum noise-band intraday trend: SPY 2007-2024, Sharpe 1.33 net, positions closed by end of day. It is directly portable to ES/NQ. — [Concretum](https://concretumgroup.com/beat-the-market-an-effective-intraday-momentum-strategy-for-sp500-etf-spy/)
- Some managed-futures funds now hold small bitcoin futures positions, e.g. WisdomTree WTMF long 1.5%. No correlation figure is given. — [WisdomTree](https://www.wisdomtree.com/us/insights/blog/wtmf-the-first-managed-futures-etf-to-hold-bitcoin-futures/pdf)
- Bitcoin trend studies report negative or no correlation with traditional indices (secondary summary). — [Harbourfront Quant](https://harbourfrontquant.substack.com/p/bitcoin-trend-following-strategies)
- Diversified carry has near-zero skew; individual-asset carry has fat tails. Single-market carry on a small 30-contract universe loses most of the diversification benefit. — [etf.com Swedroe](https://www.etf.com/node/93939.md)

### Inferences
- Universe: the 29 listed markets cover 4 equity, 4 energy, 5 metals, 5 grains, 2 livestock, 4 rates and 6 FX. That is enough for a reduced trend+carry book. Expect a lower Sharpe than the 155-market F7/F9 (fewer independent bets, roughly 8-12 effective). Carry is only meaningful in energy, grains, livestock, rates curve and FX (rate differential).
- Contract sizing: on a $50-150k prop account, full-size CL, NG, ZB, GC, LE etc. cannot be risk-parity-sized. Micros exist for ES, NQ, YM, RTY, CL, GC, SI, HG and the FX majors, but not for HO, RB, ZL, ZM, LE, HE or PL. Minimum-position granularity therefore forces dropping or overweighting markets (sizing knowledge; not sourced here).
- Intraday-only (Topstep): restrict to intraday momentum / noise-band breakout on ES/NQ (and possibly CL, GC, ZN, 6E), pre-registered and with the 50% haircut applied to the published 1.33 Sharpe.
- Crypto correlation: crypto trend and futures trend both go long risk in momentum-driven risk-on phases, but the trend signals rarely align across asset classes. My inference is a low positive correlation, around 0.0-0.3, which the project should compute directly from its own F7/F9 and crypto-trend return series. Gen40 already has the MT5/crypto diversification data.

### Gaps
- No published correlation between SG Trend / CTA indices and BTC trend strategies was found.
- No published intraday carry or term-structure strategy was found.
- No prop-firm-specific study of trend under trailing-drawdown rules was found.
- Current exact prop rules (Topstep overnight prohibition; CFD firms allowing overnight or weekend holds) were not re-verified in this scan.

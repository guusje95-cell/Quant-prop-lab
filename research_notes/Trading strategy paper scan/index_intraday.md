# Systematic intraday and short-horizon strategies on equity index futures and CFDs (2015-2026)

Method note: direct page fetches were blocked in this session (the egress proxy refused nd.edu, concretumgroup.com, arxiv.org and mql5.com), so every finding below comes from search-result abstracts and summaries. Exact parameters I could not confirm from a source are listed under Gaps. They are not stated as facts.

Project context: these were tested earlier and rejected or left open. Gao et al. half-hour momentum: Sharpe -1.06 on US500 CFD. Noise-area breakout: US100 Sharpe 0.71 at 1 bp, 1.12 at 0.3 bp. Euro-open: failed on limited data. Liu & Tse overnight: rejected. Turn-of-month: TEST 0.34 / VAL -0.40. The new evidence below mostly confirms those negative results.

## Q1. Opening-range breakout, VWAP trend, noise-area intraday momentum, Baltussen et al. hedging demand, end-of-day effects

### Takeaway
The Concretum/Zarattini family reports high Sharpe ratios (1.33 to 2.8), but every out-of-sample or independent check found so far is much weaker:
- **Noise-area SPY:** OOS Sharpe 0.39 for May 2024 to March 2026. A GitHub replication on SPY and ES says Sharpe has been near zero since 2025.
- **ORB on indices:** gross edge reproduced, net edge about zero on five index CFDs.
- **VWAP trend:** public replications are far below the reported figures.

Unconditional market intraday momentum (rest of day predicting the last 30 minutes) looks dead in SPX data from the 0DTE era (2022 onward). One analysis finds it survives only on days when dealers are short gamma. Single-stock ORB on "Stocks in Play" is the only variant with a strong independent replication (QuantConnect Sharpe 2.4), but it trades equities, not index futures.

### Cited Findings

**A. Zarattini & Aziz (2023), "Can Day Trading Really Be Profitable?" (SSRN 4416622): 5-minute ORB on QQQ/TQQQ**
- **Rule:** if the first 5-minute bar of the cash session is up (down), buy (sell) at the start of the second 5-minute bar. No trade when the first bar's open and close are about equal. — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/day-trading-with-an-opening-range-breakout-strategy)
- **Stop and target:** stop at the other side of the first bar. Target is 10R or the session close, so the trade is flat by the end of day. — [MQL5 replication blog](https://www.mql5.com/en/blogs/post/776235) (secondary)
- **Reported results:** hit rate about 24%, +0.13R per trade, about 33% a year on QQQ at 4x leverage. — [MQL5 replication blog](https://www.mql5.com/en/blogs/post/776235) (secondary)
- **Cost assumptions:** commissions only, with no spread or slippage, and no out-of-sample period. — [MQL5 replication blog](https://www.mql5.com/en/blogs/post/776235)
- **Failed replication:** five index CFDs tested. Gross edge reproduced on the Nasdaq-100 contract, but no market is distinguishable from zero after costs ("gross reproduced, net zero"). — [MQL5 replication blog](https://www.mql5.com/en/blogs/post/776235)

**B. Zarattini, Barbon & Aziz (2024), "A Profitable Day Trading Strategy for the U.S. Equity Market" (SFI RP 24-98, SSRN 4729284): 5-minute ORB on "Stocks in Play"**
- **Universe and sample:** more than 7,000 US stocks, 2016-2023. Stocks in Play are stocks with abnormally high activity on the day, mostly news-driven. — [Barbon paper page](https://abarbon.com/papers/a-profitable-day-trading-strategy-for-the-u-s-equity-market); [RePEc](https://ideas.repec.org/p/chf/rpseri/rp2498.html)
- **Reported results:** the top-20 Stocks-in-Play portfolio returned more than 1,600% net, with Sharpe 2.81 and annualized alpha 36%. The S&P 500 returned 198% over the same period. — [RePEc / search abstract](https://ideas.repec.org/p/chf/rpseri/rp2498.html)
- **Replication:** QuantConnect reproduction reports Sharpe about 2.4 with beta near zero, using an implementation that differs from the paper. — [QuantConnect forum](https://www.quantconnect.com/forum/discussion/18444)
- **Relevance here:** this is not an index-futures strategy. It needs a single-stock universe with intraday volume data.

**C. Zarattini & Aziz (2023), "VWAP: The Holy Grail for Day Trading Systems" (Concretum / SSRN)**
- **Rule:** long when price is above VWAP, short when below. Intraday on QQQ, with TQQQ as a leveraged variant. Sample: 2018-01-02 to 2023-09-28. — [Concretum](https://concretumgroup.com/volume-weighted-average-price-vwap-the-holy-grail-for-day-trading-systems/)
- **Reported results:** $25k grew to $192,656 net of commissions on QQQ. — [Concretum](https://concretumgroup.com/volume-weighted-average-price-vwap-the-holy-grail-for-day-trading-systems/)
- **Secondary figures:** Sharpe about 2.1 and max drawdown 9.4%, against QQQ buy-and-hold Sharpe 0.7. These come from a Bear Bull Traders summary only. — [Bear Bull Traders](https://bearbulltraders.com/?p=2606339)
- **Replications:** QuantConnect notes several public replications reported far lower numbers. — [QuantConnect backtest](https://www.quantconnect.com/terminal/cache/embedded_backtest_b115d0894231d55994b1068202f6c0ae.html); a "VWAP_trend" report shows live Sharpe -0.6, though its provenance is unclear — [QuantConnect report](https://www.quantconnect.com/reports/2dd44a5c1394e0ba3de9c7f4d7dc0716)

**D. Zarattini, Aziz & Barbon (2024), "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)" (SFI RP 24-97; revised Feb/Apr 2025): the noise-area strategy, already tested in this project**
- **Reported results, 2007 to early 2024:** 1,985% total return net of costs, 19.6% annualized, Sharpe 1.33. — [SFI](https://www.sfi.ch/de/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy); [Concretum](https://concretumgroup.com/beat-the-market-an-effective-intraday-momentum-strategy-for-sp500-etf-spy/)
- **Mechanics:** positions open on signs of demand/supply imbalance and use dynamic trailing stops. The paper also tests volatility regimes and dealer gamma imbalance as predictors. — [SFI](https://www.sfi.ch/fr/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy)
- **Boundaries and stops:** noise boundaries come from average intraday moves over the previous 14 days. Signals are checked every 30 minutes (HH:00/HH:30). Trailing stops use the noise boundaries plus VWAP, and exposure scales with current volatility. — [Bear Bull Traders MoneyShow deck](https://bearbulltraders.com/wp-content/uploads/2024/08/Money_Show_Final.pdf)
- **New post-publication evidence (key):**
  - Sheimy Paz, "Out-of-Sample Evaluation of an Intraday Momentum Strategy for the S&P 500 ETF (SPY)" (SSRN 7290621). The in-sample replication matches the paper. On May 2024 to March 2026 OOS data, Sharpe falls to 0.39, while buy-and-hold returned 29.5%. The author discusses microstructure change and 0DTE growth as causes. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7290621)
  - Independent GitHub replication on SPY and ES futures with ex-ante frozen protocols. Trade-level stats match the paper, but the edge has compressed since 2025, with recent Sharpe near zero on both instruments. — [GitHub codecat-ops](https://github.com/codecat-ops/zarattini-2024-momentum-spy)
  - arXiv 2605.04004 (May 2026), "Structural Limits of OHLCV-Based Intraday Momentum Signals in MNQ Futures: A Systematic Falsification Study". The title signals negative results on Micro Nasdaq futures, but I could not read the full text. — [arXiv](https://arxiv.org/pdf/2605.04004)
  - QuantConnect users report Sharpe of about 0.7-0.8 when the rule is moved to NQ/QQQ. That closely matches this project's US100 Sharpe of 0.71 at 1 bp. A Sharpe of 3.1 on the same thread was flagged as model-selection inflated. — [QuantConnect forum](https://www.quantconnect.com/forum/discussion/15192)
  - A TradingView implementer found results "not as good as stated", with low Sharpe and margin calls once margin checks were on. — [TradingView script](https://es.tradingview.com/script/gJeM3LZ5-Out-of-the-Noise-Intraday-Strategy-with-VWAP-YuL)

**E. Baltussen, Da, Lammers & Martens (2021), "Hedging Demand and Market Intraday Momentum", JFE 142(1):377-403**
- **Finding:** in more than 60 futures from 1974 to 2020, the return over the rest of the day positively predicts the return in the last 30 minutes before the close. The effect reverts over the following days. — [RePEc](https://ideas.repec.org/a/eee/jfinec/v142y2021i1p377-403.html); [SSRN 3760365](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365)
- **Mechanism:** gamma hedging by market makers in options and leveraged ETFs. The gamma analysis uses SPX options. — [Alpha Architect](https://alphaarchitect.com/hot-topic-does-gamma-hedging-actually-affect-stock-prices/)
- **Reported Sharpe:** 0.87-1.73 at the asset-class level (secondary summary). — [Harbourfront Quant](https://harbourfrontquant.substack.com/p/market-intraday-momentum-and-hedging)
- **Fit:** pooled OOS R² of 2.88% for equity futures, significant in 14 of 17 index futures (secondary summary). — [danfin.net](https://danfin.net/intraday-momentum-final-30-minutes)
- **Post-2022 status:** a re-test on 1,085 SPX sessions from April 2022 finds slope +0.006 (t = 0.6), with year-by-year signs alternating. Conditional on dealers being estimated short gamma at 15:30, the slope is +0.055 (t = 3.1). This is an unverified blog analysis. — [dev.to / FirmTape](https://dev.to/firmtape/intraday-momentum-is-dead-in-the-0dte-era-we-measured-it-on-1085-spx-sessions-43g0)
- **Related, Gao, Han, Li & Zhou (2018 JFE):** first half hour predicts last half hour in SPY, 1993-2013. — [SSRN 2440866](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866). Already rejected in this project.

**F. Baltussen, Da & Soebhag (2024/25), "End-of-Day Reversal" (SSRN 5039009; EFMA 2024; 2nd prize, Quantpedia Awards 2025)**
- **Finding:** individual stocks show sharp cross-sectional reversals in the last 30 minutes, driven by buying of intraday losers. The authors link this to attention-driven retail buying and short-seller risk management, not gamma or liquidity. At the market level, momentum remains. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5039009); [EUR news](https://www.eur.nl/en/news/end-day-reversal-pattern-second-place-quantpedia-awards-2025); [OptionMetrics](https://optionmetrics.com/research/a-soebhag-g-baltussen-and-z-da-end-of-day-reversal/)
- **Signal construction:** return from the prior close to about 15:30 ET, then rank stocks. — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/buy-intraday-loser-stocks-in-the-last-half-hour/)
- **Relevance here:** a cross-sectional stock strategy, not directly tradable on a single index future.

**G. Li, Sakkas & Urquhart (2022), "Intraday time series momentum: Global evidence and links to market characteristics", Journal of Financial Markets 57:100619**
- **Finding:** in 16 developed markets, intraday time-series momentum is significant both in sample and out of sample in most countries. It is stronger when liquidity is low, volatility is high, and information arrives in discrete bursts. — [Reading accepted version](https://reading-9.eprints-hosting.org/95566/1/Accepted-Version.pdf); [Nottingham repository](https://nottingham-repository.worktribe.com/output/5273197)
- **Relevance here:** the most relevant multi-market evidence for DAX, FTSE and Nikkei. It ends before the 0DTE era.

### Inferences
- Several independent sources converge (SSRN OOS paper, GitHub ES replication, FirmTape SPX test, the MNQ falsification title). The unconditional "trend into the close" edge on US index futures appears to have decayed sharply around 2022-2025. A likely cause is 0DTE flow changing dealer gamma positioning. This matches the project's own noise-area result (US100 0.71 at 1 bp). Priority for futures data is to test 2024-2026 separately before spending effort on full-sample Databento runs.
- The only surviving variant with a plausible mechanism is momentum conditioned on dealer gamma. It needs an estimate of SPX dealer gamma exposure, from options open interest or a vendor GEX feed, and none is in the current data stack. A cheap proxy to test: trade only on days with a large absolute rest-of-day move or when VIX is above its median. The JFE paper reports the effect is stronger on high-volatility and large-move days.
- ORB on index products appears to be a gross-only edge: the costed CFD replication found nothing. On ES/NQ with a 0.25-point tick, round-trip cost is about 0.5 to 1 tick plus commission, which is small relative to the 5-minute opening range on NQ. That makes NQ futures the only index venue worth one quick re-test. Its hit rate of about 24% gives long losing streaks, which conflict with a 3-5% daily prop limit only if risk per trade is above about 1%.
- Non-US indices (DAX, FTSE, Nikkei) have less 0DTE contamination, so momentum into the close may have decayed less there (Li-Sakkas-Urquhart). This is the most promising untested direction for the Dukascopy CFD data. It is a hypothesis, not a finding.

### Gaps
- I could not read the full Baltussen et al. JFE paper. Exact S&P 500-only Sharpe, cost treatment, and the negative-gamma versus positive-gamma return split remain unconfirmed.
- Exact noise-area parameters remain unconfirmed: band multiplier, gap adjustment, volatility target and leverage cap, and the commission and slippage the paper assumes. My recollection of a 2% daily vol target, 4x cap and $0.0035/share commission is unconfirmed and should be checked against the paper.
- I could not read the arXiv MNQ falsification paper (2605.04004), the Quantitativo "Intraday Momentum for ES and NQ" post, or the MQL5 per-index net figures.
- I found no peer-reviewed post-2022 replication of Baltussen et al. on ES futures.

## Q2. Overnight vs intraday decomposition and the European open

### Takeaway
Two papers place the US equity premium in the hours around the European open:
- **Bondarenko & Muravyev (JFQA 2023):** 4 hours around the European open earn the whole ES return, with Sharpe about 1.6 that remains high after costs.
- **Boyarchenko, Larsen & Whelan (RFS 2023):** same timing, explained by dealer inventory. Returns depend on order imbalance at the prior US close, and selloffs reverse more than rallies.

A related NY Fed / CXO summary indicates that bid-ask spreads can flip simple overnight-window returns negative. For prop firms that require flat by end of day, a trade held through the US overnight session is generally not allowed on futures accounts. It may be allowed on CFD prop accounts.

### Cited Findings
- **Bondarenko & Muravyev, "Market Return Around the Clock: A Puzzle", JFQA 58(3):939-967 (2023):**
  - **Finding:** in E-mini S&P futures, the 4 hours around the European open account for the entire average market return. The remaining 20 hours average about zero. — [RePEc](https://ideas.repec.org/a/cup/jfinqa/v58y2023i3p939-967_1.html); [Alpha Architect](https://alphaarchitect.com/market-return-around-the-clock/)
  - **Performance:** the "EU-open" window, roughly 23:30 to 03:30 ET, returns 7.6% a year with Sharpe 1.67 (t = 6.4) on a 2004-2018 sample (secondary). The published abstract gives Sharpe 1.6, says returns remain high after transaction costs, and says results were stronger in 2020 COVID. — [Alpha Architect](https://alphaarchitect.com/market-return-around-the-clock/)
  - **Mechanism:** European investors resolve uncertainty accumulated overnight. VIX futures rise overnight and fall around the European open. — [Alpha Architect](https://alphaarchitect.com/market-return-around-the-clock/)
- **Boyarchenko, Larsen & Whelan, "The Overnight Drift", RFS 36(9):3502-3547 (2023), NY Fed SR 917:**
  - **Finding:** large positive US equity returns during the European opening hours, strongly related to order imbalances at the previous US close, consistent with inventory risk. — [RePEc RFS](https://ideas.repec.org/a/oup/rfinst/v36y2023i9p3502-3547..html); [NY Fed SR917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf)
  - **Asymmetry:** selloffs produce larger overnight reversals than rallies. — [RePEc](https://ideas.repec.org/p/fip/fednsr/87539.html)
  - **Timing:** the NY Fed blog post (1998-2019 sample) places the largest returns at 02:00-03:00 ET. A CXO summary notes that accounting for bid-ask spreads flips average return and Sharpe negative in that study's implementation. — [Liberty Street](https://libertystreeteconomics.newyorkfed.org/tag/sp-500/); [CXO Advisory](https://www.cxoadvisory.com/?p=33743)

### Inferences
- The tradable refinement from Boyarchenko et al. is conditional: go long ES around 02:00-03:00 ET only after a down US close or a sell-imbalance at the close, because selloffs reverse more strongly. This conditional version may survive costs better than the unconditional window that failed in this project on US500 CFD. It suits Databento ES 1-minute data, where the 0.25-point tick costs about 0.5 bp. Overnight CFD spreads on Dukascopy are wider, which may explain the earlier CFD failure.
- The trade runs inside the US overnight session, so for futures prop firms it is "flat by end of day" only if the trading day is defined as the CME session (17:00-16:00 CT). This needs checking per firm.

### Gaps
- I did not find the exact order-imbalance proxy used by Boyarchenko et al., or their net-of-cost Sharpe for an ES implementation.
- I found no post-2023 out-of-sample test of either the European-open effect or the conditional reversal.
- I did not obtain sources for Lou, Polk & Skouras (2019, JFE) "A tug of war" or the Kelly & Clark overnight papers. Both are cross-sectional or ETF-based, and I found no tradable index-futures rule.

## Q3. FOMC drift, macro announcements, OPEX week, turn-of-month

### Takeaway
- **Pre-FOMC drift:** disappeared after 2015 (Kurov, Wolfe & Gilbert, FRL 2021). One paper says it persists only when implied volatility is high.
- **Pre-CPI:** I found no peer-reviewed evidence of a pre-CPI drift.
- **OPEX week:** the old premium (1983-2008) has turned negative or noisy since 2021, according to practitioner sources only.
- **Turn-of-month:** no new evidence found. The project's earlier rejection stands.

### Cited Findings
- **Lucca & Moench (2015, JF):** since 1994, more than 80% of the US equity premium was earned in the 24 hours before scheduled FOMC announcements. The effect is absent in 1970-1993. — [Liberty Street Economics](https://libertystreeteconomics.newyorkfed.org/2012/07/the-puzzling-pre-fomc-announcement-drift)
- **Kurov, Wolfe & Gilbert, "The Disappearing Pre-FOMC Announcement Drift", Finance Research Letters 40 (2021):** with data extended to December 2019, the drift essentially disappeared after 2015, with or without press conferences. The authors suggest lower uncertainty as a cause. — [PDF](https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf); [RePEc](https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html)
- **Martello & Ribeiro (SSRN 3286745):** the pre-FOMC drift averages 109 bp when implied volatility is above its prior median and 9.7 bp when below. They argue the recent disappearance may reflect time variation also seen in older data. — [Quantpedia](https://quantpedia.com/fomc-equity-drift-occurs-in-periods-of-high-uncertainty/)
- **Cujean (Bern):** links the drift's disappearance to new Fed communication policy, describing a switch between equilibria. — [Carlo Alberto seminar](https://carloalberto.org/event/julien-cujean-university-of-bern)
- **Insper thesis, 1-minute E-mini data, 1997-2020:** pre- and post-FOMC returns are negatively related. A reversal strategy has a Sharpe about 2.5 times that of the pre-FOMC drift. This is an unrefereed thesis. — [Insper repository](https://repositorio.insper.edu.br/handle/11224/7532)
- **OPEX week, 1983-2008:** S&P 500 and large-cap returns are elevated in option-expiration week. — [CXO Advisory](https://cxoadvisory.com/calendar-effects/option-expiration-week-stock-return-drill-down)
- **OPEX week, since 2021:** S&P 500 weak in expiration weeks, especially quarterly ones. Possibly random, and the proliferation of expirations dilutes the monthly date. — [Schaeffer's](https://www.schaeffersresearch.com/content/analysis/2023/03/08/caution-potentially-volatile-week-ahead)
- **OPEX week, full history:** Quantified Strategies reports CAGR of 2% at about 18% time in market. This is a conflicting practitioner backtest. — [Quantified Strategies](https://quantifiedstrategies.substack.com/p/the-options-expiration-week-effect-aa2)

### Inferences
- Pre-FOMC long, from about 14:00 ET the day before to 13:55 ET on announcement day, is not intraday-flat and only about 8 events a year. Even if it revived in high-VIX regimes, it is a small overlay, not a core strategy.
- The FOMC-day reversal (fade the pre-announcement move after 14:00 ET) is intraday and testable on Databento ES. It has only about 8 events a year, so statistical power is low.
- Calendar effects (OPEX, turn-of-month, FOMC) all show post-publication decay or regime dependence. Their low frequency makes them unsuitable as a primary Sharpe ≥ 0.8 engine.

### Gaps
- I found no academic study of pre-CPI or pre-NFP equity drift, or of intraday CPI/NFP-day patterns, for 2015-2026.
- I found no post-2019 peer-reviewed update on the FOMC drift covering the 2022-2023 hiking cycle.
- I found no recent academic OPEX paper.

## Q4. Short-term mean reversion in index futures (RSI(2), gap fade, 5-day reversal)

### Takeaway
I found no independent, peer-reviewed post-2008 out-of-sample validation of Connors RSI(2) on the S&P 500. A 2016-2026 vendor backtest gives 1.7% a year with a 71% hit rate and a much smaller drawdown than buy-and-hold. Academic work suggests index serial correlation moved to slightly negative after index futures were introduced, and futures show weekly reversal, mostly after large declines. The evidence base is weak.

### Cited Findings
- **Backtrex, SPX500 CFD daily, 2016-2026:** rule is RSI(2) below 5 with a 200-day SMA filter. Results: +18.1% total (1.7% a year) against +255% buy-and-hold; win rate 71%, profit factor 1.43, 73 trades, max drawdown -21.5% against -35%. — [Backtrex](https://backtrex.com/en/backtests/connors-rsi-2-sp-500)
- **Baltussen, van Bekkum & Da:** across 21 global indexes, serial dependence switched from +0.038 to -0.005 after index futures were introduced, in a sample to mid-2013 (secondary summary). — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/effect-of-tracking-products-on-short-term-equity-index-trendingreversal)
- **Wang, futures weekly reversal:** strong weekly reversal in futures, concentrated after large market declines. — [Quantpedia](https://quantpedia.com/strategies/short-term-reversal-with-futures)
- **Very short horizons:** negative microstructure autocorrelation has shortened over time, from about 20 minutes to about 10 minutes. — [arXiv review of limit order books](https://arxiv.org/pdf/1012.0349)

### Inferences
- Daily RSI(2) and 5-day reversal on ES/NQ are multi-day holds, so they do not fit intraday-flat futures prop rules. They may fit swing-allowed CFD prop accounts. The best supported conditioning is to trade reversal only after large declines and in high-VIX regimes.
- Overnight gap fade, meaning fading the gap from the RTH open toward the prior close, is the intraday-flat member of this family. It is the mirror image of ORB momentum, and the costed ORB failure gives no sign of either. I found no 2015+ published evidence for it. It is cheap to test on the project's data.

### Gaps
- I found no peer-reviewed 2015-2026 study of daily reversal or RSI(2) on index futures with costs and an out-of-sample period.
- I found no published overnight-gap-fade study on ES/NQ/DAX.

## Q5. Expected correlation with a long-only daily crypto trend strategy

### Takeaway
BTC-S&P 500 daily correlation is regime-dependent:
- **Long-run level:** about 0.09 before 2020.
- **Since 2020:** 60-day peaks of 0.65 in March 2020; a one-year rolling value of about 0.1-0.35 in 2024; a 5-year average of about 0.3.
- **Stress:** correlation spikes during selloffs.

### Cited Findings
- **2020 regime shift:** the 60-day BTC-S&P correlation hit a record 0.652 in the March 2020 crash, against a 10-year average of about 0.09 up to 2020. — [21Shares](https://www.21shares.com/it/insights/newsletter-issue-72)
- **Swings:** the correlation has flipped sign many times and tends to peak during sharp BTC pullbacks. — [The Block](https://www.theblock.co/linked/65219/security)
- **2024:** the one-year rolling BTC-SPY correlation rose from about 0.1 to above 0.35 by year end. — [Principles of BTC](https://principlesofbtc.substack.com/p/how-much-is-bitcoin-correlated-with)
- **2026 figures:** a 5-year average of about 0.30 and a 30-day reading of 0.74 (Q1-Q2 2026, vendor tool). — [Spark](https://www.spark.money/tools/bitcoin-correlation-calculator)

### Inferences
- Intraday-flat index strategies have no overnight beta, and long/short intraday momentum has near-zero average market beta (QuantConnect reports beta near zero for the Stocks-in-Play ORB). Their daily P&L correlation with a long-only crypto trend book should therefore be close to zero on average.
- The risk is in stress days. Intraday momentum strategies profit on large trending down days, when crypto also tends to fall and correlation spikes. That points to mildly negative or diversifying tail co-movement, which is favourable. Mean-reversion strategies such as gap fade and RSI(2) buy dips, so they would add losses on the same crash days as crypto trend. Their tail correlation is likely positive, which is unfavourable.
- These are inferences. The project should compute them directly from its own daily P&L series.

### Gaps
- I found no published study of the correlation between intraday index strategies and crypto trend strategies. This must be computed in-house.

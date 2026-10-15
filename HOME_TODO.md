# Status and to-do list (2026-10-14)

## A. What to do at home

**NEW (2026-10-15): start paper trading of crypto portfolio v5.** This is simulation only: public data, no keys, no orders.
1. Run `git pull`.
2. Double-click `paper_v5_start.bat`. Leave the window open and the PC awake. Alternatively, run `paper_v5_schedule.bat` once to make it an hourly background task.
3. Check it any time with `paper_v5_status.bat`.
4. Once a week, double-click `paper_v5_share.bat` to send the results to Claude.

Details are in `paper_trading/v5/README.md`; the go/no-go rules are in `config/paper_v5.json` (minimum 8 weeks).

**Must do**
1. **Get the project on your PC.** If it's already there, run `git pull` instead.
   ```
   git clone -b claude/autonomous-prop-quant-research-191f8d https://github.com/guusje95-cell/Quant-prop-lab
   ```
2. **Start the Backtest Lab once:** double-click `run_lab.bat`. The first run installs everything and downloads the basic data. It opens at http://localhost:8501.
3. **Download the Binance research data:** double-click `get_binance_data.bat`. This takes 1–3 hours, and you can stop and restart it.
4. **Share that data with Claude:**
   ```
   git add research_data
   git commit -m "Binance research data"
   git push
   ```
5. **Run the ChatGPT prompt below** and send me the papers that pass the checks, as PDFs or links.
6. **Tell me:**
   - which prop firms you will really use (Crypto Fund Trader? FTMO? others?);
   - how many accounts you plan to run;
   - your monthly budget for challenges.

**Optional (more data = better tests)**

7. **Dukascopy (free, no account, no website clicking).** Double-click these in order. Each can be stopped and restarted.
   - `get_dukascopy_1.bat`: about 3 hours. 1-minute data, 2013 to today, for US100, US500, US30, DE40, gold, EURUSD.
   - `get_dukascopy_spreads.bat`: about 1 hour. Ask prices 2023+ for the same 6 instruments, so we get the real spread per hour.
   - `get_dukascopy_2.bat`: overnight. US2000, UK100, JP225, EU50, FR40, silver, WTI, Brent, 5 FX majors, BTC and ETH CFDs.
   - `get_dukascopy_3.bat`: optional, overnight. AUS200, HK50, CH20, ES35, natural gas, copper, Bund, US T-bond, 6 more FX pairs.
   - After each one, push: `git add research_data`, `git commit -m "Dukascopy data"`, `git push`.
8. **Databento: real CME futures, using the free $125 credit.**
   1. Make a free account at databento.com. **Don't add a payment card**; then nothing can ever be charged.
   2. Copy your API key, then run `setx DATABENTO_API_KEY your_key` in a terminal and open a new terminal window. Never paste the key in chat or code.
   3. Run `pip install databento`.
   4. Double-click `get_databento_check_cost.bat`. It downloads nothing; it prints the exact cost of every item and what fits in $100. Send me the list if anything looks odd.
   5. Double-click `get_databento_download.bat`. It downloads in priority order and stops before going over $100.
   6. Push: `git add research_data`, `git commit -m "Databento data"`, `git push`.

**Not yet**
- **Don't buy a challenge yet.** First paper trade C* + BTC leads for a few weeks. I'll update the daily signal script for it (see C).

**Easiest: everything free in one go.** First `git pull`. Set Windows sleep to Never: Settings > System > Power & battery > Screen and sleep > "When plugged in, put my device to sleep after: Never". Then double-click `get_all_free_data.bat` overnight. It covers Binance (including the premium index) and all Dukascopy steps. Already-finished months are skipped, so an interrupted run loses nothing. Afterwards push `research_data`.

**Extra after the Binance download (small, a few minutes; not needed if you used get_all_free_data.bat):** double-click `get_binance_premium.bat`, then push again (`git add research_data`, `git commit -m "Binance premium index"`, `git push`). It adds the hourly perp-vs-spot premium (the basis), needed for a clean re-test of the basis papers. If it reports 'failed' for every coin, tell Claude.

## B. Prompt for ChatGPT (copy everything between the lines)

---
I'm looking for research papers on trading strategies that I can backtest myself. I trade prop-firm challenges on crypto perpetual futures (Bybit / Binance style) and possibly CME index futures. I already have a daily crypto trend-following strategy (long-only breakouts + time-series momentum on the 10 largest coins). I now need strategies that are UNCORRELATED with daily crypto trend and give STEADIER monthly returns: many small gains, few big losses, with no hidden crash risk (no martingale, grid trading, or naked option selling).

Search SSRN, arXiv (q-fin), Google Scholar, NBER, the Journal of Futures Markets, Finance Research Letters, the International Review of Financial Analysis, the Journal of Financial Economics, the Review of Financial Studies, Quantpedia and Alpha Architect. Find 10–15 papers (2018 or newer preferred) on these topics:
1. Intraday return predictability in Bitcoin and crypto: time-of-day effects, intraday momentum (first part of the day predicting the last part), US-open / Asia-open effects.
2. Funding rates or open interest of crypto perpetual futures predicting future returns (crowded longs/shorts, extreme funding, open-interest spikes).
3. Liquidation cascades and short-term price reversal or continuation in crypto futures.
4. Market-neutral crypto strategies that can be done with perpetual futures only (no spot, no options): e.g. pairs/relative value between coins, cross-sectional strategies with costs included.
5. Intraday strategies on E-mini S&P 500 / Nasdaq futures with transaction costs included and at least 10 years of data.

For each paper give:
- title, authors, year, journal or venue, and a working link (SSRN/arXiv/DOI);
- market, data period and bar frequency;
- the exact trading rules (entry, exit, holding period, sizing) in 3–6 bullet points;
- reported net Sharpe / annual return / max drawdown, and how costs were modelled (taker or maker fees, slippage);
- whether the rules are fully specified (no proprietary or black-box parts);
- whether anyone replicated it, and whether it decayed after publication;
- the data I need (e.g. 1-minute candles, funding history, open interest, liquidations) and where to get it free;
- red-flag rating (low/medium/high) for overfitting, with one sentence why.

Only list papers you can actually link to; if unsure a paper exists, say so. EXCLUDE these, which I already tested:
- Moskowitz-Ooi-Pedersen time-series momentum
- Liu-Tsyvinski crypto factors
- Gao et al. "Market Intraday Momentum"
- Baltussen et al. "Hedging Demand and Market Intraday Momentum"
- Zarattini-Aziz-Barbon "Beat the Market"
- Zarattini-Pagani-Barbon "Catching Crypto Trends"
- Moreira-Muir "Volatility-Managed Portfolios"
- Bondarenko-Muravyev "Market Return Around the Clock"
- Liu-Tse overnight returns
- de Groot et al. commodity curve momentum
- Bianchi et al. commodity curve dynamics
- Liu et al. realized semivariance momentum
- the Quantpedia Bitcoin 21:00–23:00 UTC seasonality
- Kalman/DTW pairs trading
- the MaxAI Q-learning paper

Rank the final table by how suitable each paper is for steady monthly prop-firm income.

---

## C. Where we are now

| # | Strategy | Status | Key numbers |
|---|---|---|---|
| 1 | **C\* + BTC leads** (crypto daily trend; altcoins only while BTC trends up) | **Validated, current best** | Sharpe 1.78 on the 10 majors (realistic ≈ 1.4–1.5 after the survivorship check). Max DD −13%. 50% positive months. Prop on hourly prices: CFT about $11.6k / FTMO about $12.1k average net per account over 2 years. |
| 2 | **Bitcoin 21:00–23:00 UTC window** (intraday) | **Candidate**: edge confirmed before costs out of sample; needs maker (limit) orders | Before costs, Sharpe 1.9 (2023–26). At 2 bp: Sharpe ≈ 0.8, 60% positive months, correlation with C* 0.14. C* + half-size window: positive months 49% → 60%. |
| 3–4 | Unknown yet | **To find** | Directions: open interest / funding signals, liquidation reversals, intraday breakouts, papers from the ChatGPT search. |

**Prop settings found so far**
- **CFT 1-Phase:** challenge 1.0×, funded 0.4×. No extra stops or take-profits (they did not hold up on hourly prices).
- **FTMO 2-Step:** challenge 1.5×, funded 0.6×, daily stop at 90% of the limit, 4% take-profit, 20-day vol window, 0.2 no-trade band (Gen52).
- **Which firm (Gen55, `research/GEN55_FIRMS.md`):**
  - Robust and cheap: BrightFunded Two-Step Bright, FundedNext Stellar, FTMO, HyroTrader Two-Step (about $12k net per $100k account over 2 years, about $550 fees).
  - Highest per account: HyroTrader One-Step ($14–17k).
  - Avoid: Breakout and SizeProp Degen.
  - Before buying, check each firm's algo/copy-trading rules and current prices (Breakout and BrightFunded One-Step prices were assumed).
- **More accounts multiply income**, but not consistency (one strategy: 22–33% of months with income).

**Tools:**
- Backtest Lab (`run_lab.bat`): Scorecard, Prop-firm simulator, all strategies.
- Dashboard: https://claude.ai/artifact/4M2JZaEc7DjxZEDcUaN9HU
- Research notes: `research/GEN47…GEN54*.md` and `research/LEADERBOARD.md`.

## D. What we do next (Claude)

Target: about 5-7 strategies in total, giving 2-4 per firm type (crypto / CFD / futures). Pipeline for every new data set:

1. **Test** each candidate with a written plan made before testing, using real costs and spreads.
   - Pass rule: Sharpe >= 0.8 after costs in the test period, correlation with existing strategies < 0.3, and it adds positive months.
2. **Robustness checks:** hourly or minute replay; 2x costs; one-bar delay; other markets and periods; deflated Sharpe with the full trial count.
3. **Portfolio per firm type:** which validated strategies fit each firm's markets and rules (intraday-only, leverage, swap, automation).
   - Weights follow a simple rule (equal risk), not optimised on the past.
4. **Prop settings per firm:** challenge and funded risk, daily stop, payout timing, and number and staggering of accounts.
   - Chosen on development data, then confirmed on the test period and the hourly replay.
5. **Ranking:** firms ranked by expected net profit, chance of profit and months with a payout. Dashboard and Lab updated.
6. **Execution:** daily signal script, then a paper-trading bot with safety guards (loss stop below the firm limit, kill switch, alerts) per platform (Bybit / Hyperliquid API, MT5, TopstepX).
7. **Monitoring:** live vs backtest per strategy. Replace strategies that decay, using the same process.

Order: Binance pack (crypto #2) -> Dukascopy (index / gold / FX for CFD firms) -> Databento (futures firms) -> combined portfolios and prop simulation per firm.

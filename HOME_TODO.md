# Status and to-do list (2026-10-14)

## A. What to do at home

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

7. **Dukascopy 1-minute index data** (US100 / US500, 2013+, free):
   ```
   set PYTHONPATH=src
   python -m qpl.lab.download dukascopy --symbols US100 US500 --start 2013-01-01
   ```
   Tell me when it's done; I'll add a step that packs it small enough to push.
8. **Real CME futures 1-minute data from Databento.** New accounts get $125 of free data credit.
   1. Make a free account. Don't add a payment card.
   2. Run `setx DATABENTO_API_KEY your_key`, then open a new terminal window. Never paste the key in chat.
   3. Run `pip install databento`.
   4. Run `python -m qpl.lab.download databento --symbols ES NQ --interval 1m --start 2015-01-01 --max-usd 20`.

**Not yet**
- **Don't buy a challenge yet.** First paper trade C* + BTC leads for a few weeks. I'll update the daily signal script for it (see C).

**Extra after the Binance download (small, a few minutes):** double-click `get_binance_premium.bat`, then push again (`git add research_data`, `git commit -m "Binance premium index"`, `git push`). It adds the hourly perp-vs-spot premium (the basis), needed for a clean re-test of the basis papers. If it reports 'failed' for every coin, tell Claude.

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

1. **Update the daily signal script** (`scripts/cft_e2_signal.py`) to C* + BTC leads, for paper trading.
2. **When your Binance data arrives:**
   - test whether limit orders get filled for the 21:00–23:00 window;
   - test the window as an overlay on C*'s existing positions;
   - test open-interest / funding / long-short-ratio signals;
   - test liquidation reversal and intraday breakouts on crypto 1-minute/5-minute data.
3. **Test the papers you send**, each with a written plan before testing (pre-registered), as usual.
4. **Build the combined portfolio** (strategy 1 + 2 + …) and re-run the prop simulator, aiming at more positive months and steadier payouts.
5. **Update the dashboard** with every new result.

# Backtest Lab

A local web app to backtest trading strategies on different data sets. It shows:
- the equity curve, drawdowns and exposure;
- monthly and yearly returns;
- whether an edge is real (in-sample vs out-of-sample, bootstrap range, deflated Sharpe, random-timing test, parameter sensitivity);
- results per asset and per trade;
- a Crypto Fund Trader challenge simulation, including "what if I buy N challenges".

C* (the research project's validated crypto strategy) is built in, next to a few classic strategies and two strategies from papers you supplied (see "Paper strategies" below). You can add your own as plug-in files.

## Start it (Windows)

1. Install Python 3.11 or newer from <https://www.python.org/downloads/>. Tick **"Add python.exe to PATH"** in the installer.
2. Download the project:
   - **With Git:** `git clone -b claude/autonomous-prop-quant-research-191f8d https://github.com/guusje95-cell/Quant-prop-lab`
   - **Without Git:** on GitHub, switch to that branch, then click **Code → Download ZIP** and unzip it.
3. Double-click **`run_lab.bat`** in the project folder.
   - The first run takes a few minutes: it installs packages and downloads public market data.
   - Your browser then opens the app at <http://localhost:8501>.
   - Later runs start in seconds.

**macOS / Linux:** run `bash run_lab.sh` instead.

**Manual start:**
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-lab.txt
set PYTHONPATH=src
python -m qpl.lab.setup_data
streamlit run app/lab.py
```
On macOS / Linux, use `. .venv/bin/activate` and `export PYTHONPATH=src` instead of the Windows lines.

## Using the app

The left sidebar works top to bottom.

1. **Data**
   - Pick a data set, the timeframe (hourly, 4-hour or daily), the assets and the date range.
   - Or upload your own CSV.
2. **Strategy**
   - Pick a strategy. Its description and its parameters appear below it.
3. **Costs and risk**
   - **Cost per side:** fee + slippage. Bybit taker 5.5 bp + about 2 bp slippage = 7.5.
   - **Funding / swap:** 0 on CFT's Bybit route.
   - **Per-asset volatility target.**
   - **Leverage:** 0.79 is the research C* setting, about 15% annual volatility.
4. **Honesty checks**
   - **Out-of-sample date:** tune only on data before it, and judge only on data after it.
   - **Trial count:** this deflates the Sharpe for every setting you have looked at.

The tabs on the main page:

| Tab | What it tells you |
|---|---|
| **Equity** | Growth vs buy-and-hold on the same assets, drawdowns, exposure and the full statistics table |
| **Returns** | Monthly heatmap, yearly bars, distribution of months, rolling 1-year Sharpe |
| **Edge check** | In-sample vs out-of-sample. Bootstrap 95% Sharpe range. Probability Sharpe > 0. **Deflated Sharpe** (luck-adjusted for your number of trials). Random-timing test. Parameter sweep: a real edge is a broad plateau, not one sharp peak |
| **Assets & trades** | Contribution per asset, trade count, win rate, profit factor, average holding time, full trade list |
| **Prop firm (CFT)** | Pass / fail chance per challenge attempt under CFT's 1-Phase or 2-Phase rules (equity-based daily loss on intraday lows), and the 2-year "buy up to N challenges" simulation with your account size and fee |
| **Compare strategies** | Several strategies on the same data, side by side |
| **Export** | CSV downloads of results, daily results, positions and trades |

## Better data on your PC

Your PC can reach exchanges that the research cloud could not. Each command saves a file in `data/lab/`, which then shows up in the app as **"Downloaded: …"**.

```
set PYTHONPATH=src
python -m qpl.lab.download bybit   --symbols BTCUSDT ETHUSDT SOLUSDT --interval D   --start 2020-01-01
python -m qpl.lab.download bybit   --symbols BTCUSDT ETHUSDT --interval 60 --start 2022-01-01 --name bybit_1h
python -m qpl.lab.download binance --symbols BTCUSDT ETHUSDT --interval 1d --start 2017-08-01
python -m qpl.lab.download binance --symbols BTCUSDT ETHUSDT --interval 1h --start 2020-01-01 --futures
python -m qpl.lab.download okx     --symbols BTC ETH SOL --interval 1H --start 2020-01-01
python -m qpl.lab.download yahoo   --symbols ^GSPC ^NDX GC=F CL=F EURUSD=X
python -m qpl.lab.download stablecoins
python -m qpl.lab.download yahoo   --symbols NQ=F ES=F --interval 5m
python -m qpl.lab.download dukascopy-github --symbols US100 US500 --interval M5
python -m qpl.lab.download futures-github
python -m qpl.lab.setup_data --papers
```

- **Bybit** is the closest data to what CFT trades, because CFT's Bybit route uses Bybit USDT perpetuals. Bybit intervals: `D`, `240` (4h), `60` (1h).
- **Stablecoins** is the USDT + USDC supply that C*'s stablecoin filter needs. Re-run it now and then to keep it current.
- **Your own data** (broker exports, TradingView, etc.): use **Upload a CSV file** in the app.
  - Required columns: `time`, `open`, `high`, `low`, `close`.
  - Optional columns: `symbol` (for several assets in one file) and `volume`.

## Paper strategies

Two strategies from the papers you supplied are built in. Neither can be copied 1-to-1, because parts of each paper are not published or rely on data that costs money. Each strategy's description in the app says what differs. The **Assets & trades** tab shows what each one chose or learnt per window.

### "Paper: Kalman pairs (DTW + cointegration)" (SSRN 5017127)

**How it works**
1. On a formation window (default 2 years), measure the Dynamic-Time-Warping distance between every pair of assets.
2. Cluster the assets. The number of clusters is chosen by silhouette score.
3. Run the Engle-Granger cointegration test inside each cluster and keep pairs with p < 0.05.
4. For each pair:
   - a Kalman filter estimates the hedge ratio;
   - the spread's z-score is computed over a window equal to its half-life;
   - **entry:** the z-score crosses back inside ±1.25 (delayed entry);
   - **exit:** 0.08σ past the mean.

**Data**
- **What it needs:** several related assets on daily bars.
- **What the paper used:** Chinese commodity futures. Use **"Futures daily, 250 markets"**, or `Downloaded: futures_daily` (29 US futures).
- **Chinese futures:** you can add them yourself with `pip install akshare`, then `python -m qpl.lab.download china --symbols RB0 HC0 I0 J0 JM0 ...`. The research cloud cannot reach that source, so this downloader is untested.

**Choices made where the paper is silent**
- Kalman settings (δ, τ).
- Price smoothing strength.
- Minimum and maximum z-window.
- Yearly re-selection of pairs. The paper chose pairs once; set `reselect_days` to 0 for that.

### "Paper: MaxAI Q-learning (intraday, money flow)" (Huber, preprint)

**How it works**
- **State:** 20-bar Chaikin Money Flow, rounded to 2 decimals.
- **Actions:** buy, sell or flat.
- **Learning:** tabular Q-learning with the paper's GA-tuned α 0.12, γ 0.85, ε 0.08. The reward is the next bar's return minus costs.
- **Training:** on the first year of data. After that it trades only data it has never seen.
- **Exits:** stop-loss 0.30% and profit target 0.50% (≈ the paper's $900 / $1,500 on one NQ contract).
- **Session:** US cash session only, 9:30–16:00 New York.

**Data**
- **What it needs:** 1- to 15-minute index bars.
- **What we have:**
  - "US100 CFD, Dukascopy (5-min, 2020-23)", which covers the paper's 2021 train and 2022 test years;
  - `Downloaded: nq_futures_5m_recent`, real NQ futures for the last 60 days.
- **What the paper used:** NQ 1-minute data bought from FirstRate Data.
- **Your own data:** export 1-minute NQ from TradingView, NinjaTrader or your broker as a CSV, and use **Upload a CSV file**.

**What differs from the paper**
- The paper's money-flow indicator and the GA search ranges are proprietary, so the plain Chaikin Money Flow is used instead.
- TradeStation fills stops inside the bar. Here, stops and targets are checked on bar closes, so use 1- or 5-minute bars.

**Settings to use in the app**
- **Cost per side:** set it to about 0.3 bp (NQ futures: $10 round trip on ~$300k notional). For prop-firm CFDs, use the firm's spread.
- **Leverage:** 1 = $1 of index per $1 of equity. One NQ on the paper's $83k is ≈ 3.6×.

### Intraday momentum papers (added after you asked for papers with fully published rules)

**"Paper: Market intraday momentum (Gao et al. 2018)"**
- At 15:30 New York, take the direction of the move from yesterday's close to 10:00.
- Hold it until 16:00.

**"Paper: Beat the Market noise-area breakout (Zarattini et al. 2024)"**
- Draw a band around the day's open, sized from the last 14 days' typical moves at each time of day.
- Every 30 minutes, enter when price closes outside the band.
- Exit at a trailing stop (the boundary or VWAP) or at 16:00.
- Positions are sized to 2% daily volatility, with a maximum of 4×.

**Data and costs**
- Both need 5- to 30-minute US index bars, e.g. "US500 CFD, Dukascopy (15-min)" (2013–2023).
- Both are very sensitive to cost. Set "Cost per side" to your real cost: about 0.3–0.6 bp for CME futures, about 1–2 bp for a CFD spread.

**Pre-registered results:** see `research/GEN47_INTRADAY_MOMENTUM.md`.
- **Gao:** fails, with negative Sharpe everywhere.
- **Noise-area breakout:** positive in most tests.
  - Sharpe 0.36 (US500) to 0.71 (US100) at 1 bp.
  - Sharpe 0.9–1.1 at futures costs.
  - It did not pass the strict primary test.

### What the Lab found (pre-registered defaults, every run listed, nothing tuned)

**MaxAI re-implementation on US100 5-min CFD data, cost 0.3 bp/side**

| Run | Sharpe | Return | Max DD |
|---|---|---|---|
| Paper split: train 2021, test Jan–Sep 2022 | −1.17 | −6.1% a year | −5.5% |
| Train 2020-09 to 2021-09, test to 2023-09 | −0.16 | | |
| Retrained every 90 days | −0.68 | | |

The paper reports Sharpe 1.04 for its NQ34 system. That result depends on its unpublished indicator and on 1-minute data.

**Kalman pairs, US futures, cost 2 bp/side**

| Universe | Sharpe |
|---|---|
| 29 markets, 2010–2024 | 0.19 |
| Metals + energy | 0.19 to 0.36 |
| Grains / softs / livestock | −0.21 |
| Indices + bonds | 0.16 |

- Many pairs that pass the cointegration test make no economic sense (e.g. NASDAQ / LIVE CATTLE). Cointegration on 2 years of prices finds many false pairs.
- On crypto majors the result was strongly negative (Sharpe −0.85).
- The paper's Sharpe of 4+ comes from Chinese futures with thresholds tuned on the same data. That data is not available here.

**Conclusion:** neither paper's edge showed up on the data available here. Test them on your own data before using either for a prop challenge.

## Adding your own strategy

1. Copy `strategies_user/_template.py` to a new file, e.g. `strategies_user/my_idea.py`. File names starting with `_` are ignored.
2. Change `name`, `description` and `params`, and write the `signal(bars, p)` method:
   - It returns, for every bar and asset, a target position: 1 = long, −1 = short, 0 = flat. Fractions are allowed, and up to ±2 for conviction scaling.
   - It may use only data up to and including each bar. Use `.shift(1)` for "yesterday", and never `.shift(-1)`.
   - The engine trades the signal on the next bar and handles sizing, costs and leverage.
3. Refresh the app. The strategy appears in the list. If the file has an error, the sidebar shows it.

Inside `signal`:
- `bars.close`, `bars.high`, `bars.low`, `bars.open` and `bars.volume` are tables with one column per asset.
- `bars.freq` is `1h`, `4h` or `1d`.
- `bars_per_day(bars)` helps you write lookbacks in days that work on any timeframe.

Run `python -m pytest tests/test_lab.py` to check the plug-in system and the no-look-ahead checks still pass.

## Honest use

- Every setting you try and look at is a trial. Many trials make a lucky backtest look like an edge. The app counts your trials and shows the **deflated Sharpe**: under about 50% means probably noise.
- Decide on a strategy using only data before the out-of-sample date, then look at the out-of-sample row **once**.
- Backtests assume your fills. Real slippage in fast markets, exchange outages and rule changes at prop firms are not modelled.
- CFT rules and fees in the prop tab come from third-party trackers. Check them at checkout.
- Nothing here is a guarantee of future returns or payouts.

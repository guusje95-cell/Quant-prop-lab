# Backtest Lab

A local web app to backtest trading strategies on different data sets. It shows:
- the equity curve, drawdowns and exposure;
- monthly and yearly returns;
- whether an edge is real (in-sample vs out-of-sample, bootstrap range, deflated Sharpe, random-timing test, parameter sensitivity);
- results per asset and per trade;
- a Crypto Fund Trader challenge simulation, including "what if I buy N challenges".

C* (the research project's validated crypto strategy) is built in, next to a few classic strategies. You can add your own as plug-in files.

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
```

- **Bybit** is the closest data to what CFT trades, because CFT's Bybit route uses Bybit USDT perpetuals. Bybit intervals: `D`, `240` (4h), `60` (1h).
- **Stablecoins** is the USDT + USDC supply that C*'s stablecoin filter needs. Re-run it now and then to keep it current.
- **Your own data** (broker exports, TradingView, etc.): use **Upload a CSV file** in the app.
  - Required columns: `time`, `open`, `high`, `low`, `close`.
  - Optional columns: `symbol` (for several assets in one file) and `volume`.

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

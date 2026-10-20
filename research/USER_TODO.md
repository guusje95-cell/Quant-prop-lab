# To do on your PC (when home)

**NEWEST - free data for the next crypto test (Gen247, ~30-45 min, resumable):** double-click `get_flow_data2.bat`
   (Upbit KRW hourly for the altcoins + Binance spot hourly with taker-buy volume). Then:
   `git pull --no-edit`, `git add research_data/more research_data/binance_spot`, `git commit -m "flow data 2"`, `git push`.
   If bf2 showed "error: no Dukascopy hourly data for US100": `git pull --no-edit`, then close and restart `paper_bf2_start.bat`.

**DONE - start the two new paper traders (simulation only, no keys, no orders):**
   - `git pull --no-edit` first.
   - Double-click `paper_v7_start.bat` (crypto v7 = v6 + ridge ML, HyroTrader 2-Step $200k rules, risk 2.0, daily stop 2.5%).
   - Double-click `paper_bf2_start.bat` (new BrightFunded book bf2 = bf + ridge ML + US100/US500/US30 index sleeve, $200k, risk 2.0).
   - Leave both windows open (PC awake). Each installs scikit-learn once if missing. The first run catches up the market data
     (Upbit, USD/KRW, Deribit DVOL, Coinbase; bf2 also Dukascopy index bars) and can take a few minutes.
   - If Dukascopy throttles you, bf2 waits at most 1 hour per bar and then continues; the reconciliation later shows any effect.
   - Once a week: `paper_v7_share.bat` and `paper_bf2_share.bat` (pushes ledger/status, not market data).
   - The old v5/v6/bf traders can keep running side by side; they are not changed.

0. **Intraday-edge data (new):**
   - a. Double-click `get_squeeze_dix.bat` (free SqueezeMetrics GEX/DIX). If it fails, open https://squeezemetrics.com/monitor/static/DIX.csv in your browser and save it as `research_data\more2\squeeze_dix.csv`. Push it.
   - b. Double-click `get_databento_quotes.bat`: it only PRINTS prices (order flow, top of book, 1-second bars, ES options for gamma exposure). Downloads nothing, costs nothing. Send Claude the printed prices.

1. **Extra futures roots** (priority order: UB ultra bond, NKD Nikkei, PL platinum, TN ultra 10y, EMD MidCap): double-click `get_futures_extra.bat`.
   - It shows the Databento cost per root first, then downloads roots in that order while the running total stays within the amount you type (~$50 credit left).
   - Then: `git pull --no-edit`, `git add research_data/databento`, `git commit -m "databento extra roots"`, `git push`.
2. **VIX / VXN / VVIX history** (free, CBOE): double-click `get_vix_data.bat`.
   - Then: `git pull --no-edit`, `git add research_data/more2`, `git commit -m "vix data"`, `git push`.
3. **Dukascopy daily history 2003-2026** (free, slow: about 1 hour, resumable): double-click `get_dukascopy_daily.bat`. Needed for the gold/platinum test and the 2003-2010 backcasts.
   - Then: `git pull --no-edit`, `git add research_data/dukascopy_daily`, `git commit -m "dukascopy daily"`, `git push`.
4. Earlier open items: Deribit download (`get_deribit_fast.bat`, then push); check BF spreads for SNX/INJ/HBAR/SUI/OP in MT5; one demo round trip to see whether the commission is per deal or per round trip.

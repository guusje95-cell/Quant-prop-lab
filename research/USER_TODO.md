# To do on your PC (when home)

**WHEN BACK AT THE PC (2026-10-23):**
   1. `git pull --no-edit`
   2. bf26 index-feed check: `git add -f paper_trading/bf26/data/dukascopy` then `git commit -m "bf26 index feed files"` and `git push`
   3. Run `paper_v86_share.bat` and `paper_bf26_share.bat`; push `research_data/binance_pit` when get_binance_pit.bat is done.

**NEWEST (2026-10-21, latest) - v8.6 and bf2.6 (wide premium carry with inverse-vol legs + tranched rebalancing; v 2.750 -> 3.110, bf2 2.506 -> 2.829). Start these two paper traders (they replace every earlier v8.x / bf2.x):**
   1. `git pull --no-edit`
   2. Crypto: `paper_v8_share.bat` once (or `paper_v83_share.bat` / `paper_v84_share.bat` if you started those), close that window,
      then double-click `paper_v86_start.bat` (v8.6; not v85). First run: downloads the 40 extra coins (Binance perps) and Binance spot BTC/ETH.
   3. CFD: `paper_bf2_share.bat` once, close the bf2 window, then double-click `paper_bf26_start.bat` (bf2.6; not bf24).
   3b. NEW: send the support questions in research/FIRM_RULES_EXECUTION.md (section 4) to HyroTrader and BrightFunded and paste me
      the answers - especially HyroTrader's daily drawdown (4% or 5%) and whether API automation is allowed.
   4. CHECK ON BYBIT (HyroTrader): are these USDT perps listed? 1000PEPE, 1000SHIB, 1INCH, ALGO, APE, APT, ARB, AXS, CHZ, COMP, CRV,
      DASH, DYDX, EGLD, ENJ, GALA, GRT, HBAR, ICP, IMX, INJ, IOTA, KSM, LDO, MANA, NEO, OP, RUNE, SAND, SNX, STX, SUI, SUSHI, THETA,
      TIA, WLD, XTZ, YFI, ZEC, ZIL. Tell me any that are missing.
   5. Push the Bithumb data when done; optional `get_deribit_options.bat` (options skew / flow, Gen309 ready).
   5b. NEW (15-30 min, free): `get_bybit_check.bat` - Bybit listings, order sizes, funding history and spreads for our 60 coins
      (what v8.6 really costs on HyroTrader). Then `git add research_data/bybit`, commit, push.
   6. IMPORTANT for trusting v8.5 (overnight, free, a few hours, resumable): `get_binance_pit.bat` - every Binance USDT perp ever
      listed, delisted ones too. It tests whether the wide-carry gain survives without survivorship bias (Gen321 pre-registered).
      Then `git add research_data/binance_pit`, commit, push.

**OLDER:** NEWEST (2026-10-21, latest) - v8.4 and bf2.3 found (ridge + variance risk premium + weekend features, CFD book + altcoin kimchi; v 2.700 -> 2.750, bf2 2.427 -> 2.506): switch BOTH paper traders:**
   1. `git pull --no-edit`
   2. Crypto: `paper_v8_share.bat` once, close the v8 window (or v8.3 if you already started it: `paper_v83_share.bat`),
      then double-click `paper_v84_start.bat` (v8.4 = v8.3 + better ridge features, 2.700 -> 2.750; replaces v8.3).
   3. CFD: `paper_bf2_share.bat` once (keeps bf2's record), close the bf2 window, double-click `paper_bf23_start.bat` (bf2.3; not bf22).
      The first run downloads Binance spot BTC/ETH hours since 2026-10-20 (a few seconds) - Binance works from your PC.
   4. Push the Bithumb data when its download is done.
   5. NEW free data (30-90 min, resumable): double-click `get_deribit_options.bat` - Deribit options trade history (BTC, ETH,
      2020-today) reduced to daily put/call flow and implied vol by strike: options skew and options flow, never tested
      (history.deribit.com is blocked from the cloud). Then `git add research_data/deribit_options`, commit, push.

**NEWEST (2026-10-21, later) - v8.3 found (volatility-scaled ridge + inverse-vol premium carry): switch the crypto paper trader v8 -> v8.3:**
   1. `git pull --no-edit`
   2. `paper_v8_share.bat` once (keeps v8's record), close the v8 window, then double-click `paper_v83_start.bat`.
   3. bf2 keeps running unchanged. Push the Bithumb data when its download is done.

**NEWEST (2026-10-21) - v8 found (v7 + kimchi premium on altcoins), and the next free data:**
   1. `git pull --no-edit`.
   2. Switch the crypto paper trader from v7 to v8 (v8 contains every v7 sleeve, logged per sleeve):
      `paper_v7_share.bat` once (keeps v7's record), close the v7 window, then double-click `paper_v8_start.bat`.
      The first run downloads Upbit history for 16 altcoins (a few minutes).
   3. Leave bf2 running unchanged (its research gain, +0.005, is too small to restart the paper run for).
   4. Double-click `get_flow_data3.bat` (free, ~30-60 min, resumable): Upbit for the 40 extra coins + Binance TRY/BRL/EUR pairs + FX.
      Then `git pull --no-edit`, `git add research_data/more research_data/binance_fiat`, `git commit -m "flow data 3"`, `git push`.
   4b. OPTIONAL (free, 30-90 min, Google rate-limits): `get_google_trends.bat` - daily Google search interest for crypto terms
      (retail attention, from the Koch & Dimpfl paper). Then `git add research_data/attention`, commit, push.
   4c. OPTIONAL (free, 20-40 min): `get_bithumb.bat` - Bithumb (second Korean exchange) hourly candles; tests a two-venue
      Korean premium (Gen277). Then `git add research_data/more`, commit, push.
   5. Papers that would help (PDF in the chat; not committed): Makarov & Schoar 2020 "Trading and arbitrage in cryptocurrency
      markets" (JFE); Choi, Lehar & Stauffer 2022 "Bitcoin microstructure and the kimchi premium"; any paper on retail /
      regional crypto demand or on Upbit/Bithumb flows.

**NEWEST - free data for the next crypto test (Gen247, ~30-45 min, resumable):** double-click `get_flow_data2.bat`
   (Upbit KRW hourly for the altcoins + Binance spot hourly with taker-buy volume). Then:
   `git pull --no-edit`, `git add research_data/more research_data/binance_spot`, `git commit -m "flow data 2"`, `git push`.
   If bf2 showed "error: no Dukascopy hourly data for US100": `git pull --no-edit`, then close and restart `paper_bf2_start.bat`.

**OPTIONAL big job (overnight, free): `get_trade_size_flow.bat`** - BTC/ETH perp trades split by trade size (whale vs small
   flow), 2020 to last month, from the public Binance archive. Tens of GB download, processed one month at a time and deleted;
   ~5 GB free disk needed. Resumable. Then `git add research_data/trade_size`, commit, push.

**Dukascopy:** run at most ONE Dukascopy download at a time while bf2 paper trades (parallel downloads get the connection blocked,
   which also starves bf2's live index bars).

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

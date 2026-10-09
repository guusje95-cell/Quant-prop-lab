# V6 Data Catalog

Reachability (2026-10-09): **only GitHub (git clone) and PyPI are reachable**. These return proxy 403 or DNS failure:
* exchange APIs (Binance, Bitstamp, CME), binance.vision
* Kaggle, HuggingFace, FRED, Yahoo, Stooq, Nasdaq Data Link, CoinGecko, CRAN, Zenodo, OpenML
* prop-firm websites

Nothing was purchased and no credentials were used.

| Dataset | Source (pinned) | Licence | Coverage | Quality notes | Status after V6 |
|---|---|---|---|---|---|
| pysystemtrade futures (adjusted + multiple prices, FX, costs, instrument config) | github.com/robcarver17/pysystemtrade @bbe29e19 | GPL-3 | 252 instruments, 1969 → 2024-03-28; daily, hourly from ~2013 | Decimal-shift bad ticks (SUGAR_WHITE, MSCIEAFA) repaired by spike filter; SUGAR_WHITE excluded. 25 duplicate underlyings collapsed. Weekly corr with Dukascopy 0.89–0.99. Instrument list = practitioner's current list (mild survivorship). Universe 155 (rules in `futures_panel.UNIVERSE_RULES`) | DISCOVERY/VALIDATION used; **TEST 2014–19 and HOLDOUT 2020–24Q1 used once** (gen13); later re-use labelled contaminated |
| Coin Metrics community | github.com/coinmetrics/data @f1a36afb | **CC BY-NC 4.0 (non-commercial)** | 2,258 files; 139 with price; daily to 2026-05-24; MVRV, active addresses, exchange flows | Curated set incl. some dead coins (VTC, PPT, HUSD…); stablecoins/wrapped/duplicate deployments excluded by name | gen16 TRAIN used for 5 hypotheses (all rejected at TRAIN; VAL/TEST unused) |
| Bitstamp BTCUSD 1-minute | ff137/bitstamp-btcusd-minute-data @edbab565 (Zielak/Kaggle, CC BY-SA 4.0) | CC BY-SA 4.0 | 2012 → 2026-10-09 | 2012–14 illiquid; minutes forward-filled by the source | **all periods USED** (CT1 holdout viewed) |
| Binance/Bybit funding BTC/ETH | supervik/historical-funding-rates-fetcher @66a085bc | repo licence | 2020–2023 | UTC+3 timestamps fixed | USED |
| Multi-venue funding + Binance mark | ZuShen168/funding_rate_data @75c4a735 | repo licence | 2025-08 → 2026-09/10 | index_price empty → no basis; Hyperliquid/Bybit have no prices | Binance USED; Hyperliquid/Bybit unused (no prices) |
| Dukascopy CFD/FX/gold mirror | TheSnowGuru @5fa48d39 | mirror | 2007/2013 → 2023-09 | intra-week gaps (V4-A1) | USED; now also a cross-source validator |
| TopstepX CME mirror | axb0306/cme-futures-ohlc @60abd3fb | mirror | 1h 2025-03 → 2026-04 | short | index futures USED; GC/SI/CL/6E/6B/6J unused, but too short for trend lookbacks (no 2024-03..2025-03 bridge) |

## Ranked data-acquisition backlog (requires user action or a reachable host; none bought)
1. **Updated futures daily data (2024-04 → today)** in pysystemtrade format, from the user's broker or a licensed vendor. *Unlocks:* the first genuinely new out-of-sample futures period, and the input for the F9 paper book (`scripts/paper_futures_step.py`).
2. **Binance public data (data.binance.vision) spot + USD-M klines including delisted symbols.** *Unlocks:* a survivorship-free crypto universe, real perp-vs-spot basis/carry, and a CT1 test on executable perp prices instead of mark prices.
3. **Order-book / trade tape** (e.g. Binance aggTrades, CME MBO). *Unlocks:* microstructure family H (order-flow imbalance, impact, slippage models).
4. **Macro event calendar + Treasury yields** (FRED). *Unlocks:* event studies and macro-conditioned carry.
5. **Equity index options / VIX futures term structure history.** *Unlocks:* volatility risk premium research (not simulated without real option payoffs).
6. **Official prop rulebooks** (FTMO, Topstep, crypto firms). *Unlocks:* VERIFIED rule matrix.

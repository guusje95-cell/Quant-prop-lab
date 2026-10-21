# Coverage map: what has been tested (2026-10-21)

229 pre-registered protocols, about 1,456 counted trials (sum of `trials_added` in `config/gen*_protocol.json`).
Details and numbers per test: `research/LEADERBOARD.md`. "Adopted" = in a book today.

## Crypto (Binance perps, Coinbase, Upbit, Deribit, on-chain)

| Family | Examples tested | Status |
|---|---|---|
| Trend / momentum (time series) | C* ensembles, 4h breakout, 4h/6h/12h variants, vol-managed BTC/ETH, NR7, Asian range | **C*, trend 4h adopted**; rest rejected |
| Cross-sectional | momentum, reversal, residual momentum, near-high, betting-against-beta, volume shock, illiquidity, skew/MAX, IVOL, PCA stat-arb, pairs, OI growth, taker imbalance, trade size | all rejected (BAB near miss, failed replication) |
| Carry / basis | premium carry, funding TS carry, cross-exchange funding, CME basis | **premium carry adopted** |
| Liquidation / forced flow | cascade limit buys, deleveraging bounce, pump fade, funding flush, stablecoin mint | **cascade, delev bounce adopted** |
| Options / calendar | Weiss monthly expiry, weekly expiry, Friday window, turn-of-month, FOMC weeks, weekend, session windows | **Weiss (monthly) adopted** |
| Demand premia | Coinbase premium, kimchi (BTC/ETH, altcoins, idiosyncratic, bubble), USDT premium, ETH-BTC spread, composites, hourly lead-lag | **Coinbase premium (bf), altcoin kimchi (v8) adopted** |
| Flow / microstructure | taker imbalance, spot vs perp flow, trade-size flow, average trade size, opening imbalance, Upbit volume share | spot-flow ridge (bf2) adopted (noise-level) |
| Positioning | top-trader / account long-short ratios, CFTC (leveraged funds, asset managers) | rejected |
| Macro / cross-asset | VIX, US500, equity spillover, oil, DXY, stablecoin growth / dominance | rejected (stablecoin growth inside the ridge) |
| On-chain | exchange flows, MVRV, hash rate, addresses | rejected |
| Attention | Google Trends momentum, attention-spike de-risking | rejected |
| Machine learning | ridge (BTC/ETH), gradient boosting, XS ridge, altcoin ridge, hourly ridge, horizons, bagging, recency, breadth features | **ridge adopted (+ kimchi breadth = v8.1)** |
| Construction | equal risk (adopted), ERC, min-variance, inverse vol, Sharpe tilt, vol estimators, overlays, rebalance bands, maker execution | equal risk + vol targeting adopted |

## CFDs (Dukascopy, BrightFunded costs)
Index dip ensembles (R1, P1), vol-managed indices (P6) **adopted in bf2**; international indices, gold/FX/commodity trend (also swap-free),
intraday periodicity, opening-range / pre-market breakouts, FX fix, seasonality, pairs: rejected.

## Futures (Databento, 2010-26)
15-sleeve book adopted (trend, carry, calendar, dip-buying, bond convexity, energy seasonals, oil -> stocks, ...); about 240+ further
trials rejected (VIX, GEX/DIX, closing auctions, COT, auctions, spreads, extra roots, ...).

## NOT tested, and what it would take
| Idea | Why not yet | What is needed |
|---|---|---|
| Altcoin kimchi on 40 more coins, Turkish / Brazilian premia | data downloading | `get_flow_data3.bat` (Gen262 ready) |
| News sentiment (GDELT tone) | GDELT history needs Google BigQuery (free tier, Google account) | user decision |
| Order-book depth imbalance | Binance book-depth archive starts 2023 (no DEV period) | free download, but too short for our rules |
| Options skew / gamma exposure for crypto | no free history (Deribit full history is paid via Tardis) | paid data (declined) |
| Social media (X / Reddit) | no free history | paid / not available |
| A second Korean venue (Bithumb) | would make the kimchi signal less noisy | free public API, daily candles (downloader can be written) |
| Intraday futures edges | tick data costs | paid Databento (declined earlier) |

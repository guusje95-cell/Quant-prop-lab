# Extra data sources: domains to add to the cloud environment's "Allowed domains"

All of these are free, public market data. None needs an API key or account. Tested 2026-10-13: all are currently blocked by the environment's network policy.

| Priority | Domain | What it unlocks | Markets / prop firms |
|---|---|---|---|
| 1 | `datafeed.dukascopy.com` | Free tick / minute history for FX majors and crosses, gold, silver, oil, stock indices (US100, US500, DE40, …), 2003 → today | **Forex / indices / gold on MT5 prop firms** (FTMO-style, CFT MT5 route), Topstep/Lucid proxies (NQ ≈ US100, ES ≈ US500) |
| 2 | `query1.finance.yahoo.com` | Daily (and 60-day 5m) futures: ES, NQ, GC, CL, ZN, 6E…; indices; ETFs; VIX | **Futures prop firms (Topstep, Lucid)**, cross-asset daily research to 2026 |
| 3 | `stooq.com` | Daily history for futures, indices, FX, stocks (backup for Yahoo) | Same as 2 |
| 4 | `cdn.cboe.com` | VIX / VIX futures term structure history | Volatility regime signals for index futures |
| 5 | `api-pub.bitfinex.com` | Crypto candles back to 2013, plus funding and margin data | Long crypto history (pre-2019 alts) |
| 6 | `api.kraken.com` and `futures.kraken.com` | Crypto spot / perp history and funding (US-accessible) | Crypto replication venue |
| 7 | `api.exchange.coinbase.com` | Coinbase spot candles (1m–1d) | Crypto replication venue |

Already working: `www.okx.com` (crypto perps, hourly), `www.deribit.com` (BTC/ETH funding, volatility).
Geo-blocked from the server's country (we do not bypass): `api.bybit.com`, `fapi.binance.com`.

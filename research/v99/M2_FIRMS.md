# M2 (2026-11-02): other crypto prop firms for the v9.9 book, and the Netherlands / EEA access question

Source quality: web-search summaries of third-party reviews and news (the firms' own sites cannot be opened from this cloud session:
propfirmmap.com, hyrotrader.com, sizeprop.com fail DNS here). Nothing below is confirmed by a firm in writing.

## 1. The decisive fact: Bybit and EEA residents
- Bybit restricts its GLOBAL platform for EEA residents (the Netherlands included) as MiCA's transition ends on 1 July 2026; the licensed
  route, Bybit EU (Vienna), has launched WITHOUT perpetuals or options (a MiFID II licence for derivatives is reportedly applied for).
  Sources: crypto.news, cryptotimes.io (2026-06-29), coincentral.com, leodex.io.
- Consequence: every firm route that needs the trader's OWN Bybit account (HyroTrader's Bybit route, CFT's Bybit route, Fundedbit,
  Mubite-on-Bybit) is probably closed to a Dutch resident. M1's CFT account (planning ~2.04) is therefore NOT available as modelled.

## 2. Routes that remain for a Dutch resident (bot-capable)
| Route | Prices / coins | Bot | v9.9 variant (backtest -> planning) | Notes |
|---|---|---|---|---|
| HyroTrader on the **Hyro platform** | live Bybit data, 700+ USDT perps | MCP agent (task 65 adapter, dry-run) | Bybit capped 3.540 -> ~1.95 | one account per programme; MCP order / position API details unconfirmed |
| HyroTrader on **CLEO** | CLEO trades via Binance Futures API / Binance prices | CLEO markets automated bot trading; API for own code unclear | Binance-universe (R45 "as tested") capped 3.600 -> ~2.0 | earlier HyroTrader docs said API not supported on CLEO; recheck |
| **Propr** | own terminal on Hyperliquid, 160+ perps | Python SDK / API (earlier research) | HL 2.920 uncapped / 3.122 with the same 4.5% cap as the candidate -> ~1.33 / ~1.52 | 5x BTC/ETH, 2x others; $100k per account, $300k total; trailing drawdown (earlier research) |
| **BrightFunded** (CFD, MT5) | 35 crypto CFDs + indices | EAs allowed (support-confirmed) | bf2.7 2.947 -> ~1.36 | swap-free add-on |
| Mubite | Bybit or CLEO | self-developed EAs (one source) | - | 4% daily / 6% max (one-step): too tight (risk ~1.0 like MyFundedPerps) |
| Tradeify 247 (crypto) | own | futures rules: the algorithm may NOT be used at another prop firm | - | conflicts with a multi-firm plan: exclude |
| Kraken / Breakout, Bitfunded | - | manual only | - | exclude |
| Bybit / Bitget / BingX own programmes | - | - | - | none found (only competitions; BingX Elite Trader Pro 2024, non-withdrawable) |

## 3. Reading
- For a Dutch resident the realistic crypto set is **HyroTrader (Hyro platform or CLEO) + Propr (+ BrightFunded CFDs)**.
- The ~2 planning Sharpe holds at HyroTrader. Propr is ~1.33-1.52 because Hyperliquid lists far fewer of the event-short coins.
- The single most valuable open fact is whether HyroTrader's Hyro-platform / CLEO route allows our own bot with order + position
  access (MCP / API), since that is the one ~2-Sharpe route open to a Dutch resident.

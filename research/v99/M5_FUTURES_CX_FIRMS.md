# M5 (2026-11-03): futures prop firms for the futures book + CX (CME micro BTC / ETH)

Requirement: CME micro bitcoin / ether (MBT / MET) on the product list, overnight AND weekend holds (CX holds for days; the daily-flat
Topstep variant of the crypto sleeves was negative in Gen137), and bots / own automation. All claims below are from third-party
review sites (web search 2026-11-03), NOT from the firms' own rule pages. Nothing is confirmed.

| Firm | Overnight / weekend | Bots | MBT / MET | Fit |
|---|---|---|---|---|
| PropShopTrader Swing (12.5k / 25k) | yes / yes (third-party listings) | reported allowed (fundedtrading.com quotes "run your bots") | not mentioned; contract limits listed for index / energy / currency micros only | **only candidate; ask the firm about MBT / MET** |
| Tradeify (futures) | help centre: close before 16:45 ET, no overnight | allowed with conditions (own strategy, not across firms, no HFT) | not found | no (flat by close) |
| Tradeify Crypto (separate product) | overnight + weekend (reviews) | ? | crypto pairs, not CME futures | not the futures book |
| TradeDay | mostly reported NOT allowed (one outlier says yes) | conflicting; Tradovate API not exposed | micro list without crypto (MES, MNQ, M2K, MYM, M6E, MCL, MGC) | no |
| Topstep / Apex / Lucid | flat by the close | API bots (Topstep, Lucid) | crypto micros listed at some | no (daily flat) |

CME: from 29 May 2026 crypto futures trade 24/7 (broker page; subject to regulatory review, not confirmed on cmegroup.com). If so,
the weekend no longer is a closure, and the live CX should look more like its Binance proxy.

Contract rounding (`scripts/v99/fcx_lots.py`, `results/v99/fcx_lots.json`, 0 trials): with whole MBT / MET contracts the book is
2023-26 1.35-1.39 at $50k-150k (unrounded 1.414, reference without CX 1.218): the gain survives rounding. A $25k swing account is too
small for the BTC leg (median 0.06 MBT at risk 1).

Next step (user): email PropShopTrader: (1) MBT / MET on Swing accounts, (2) bots / API on Swing, (3) weekend holding of MBT / MET,
(4) contract limits for micros. Until then the futures book + CX runs only as a hub shadow.

Sources: propfirmmap.com/firms/propshoptrader, fundedtrading.com/propfirm/propshop-trader, intercom.help/tradeify (permitted times),
propfirmmap.com tradeify-crypto review, luxalgo.com/prop-firms/tradeday, tradecopia.com/propfirms/tradeday, blog.traderspost.io (TradeDay),
optimusfutures.com (CME 24/7 crypto).

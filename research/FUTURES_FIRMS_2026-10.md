# Futures prop firms (2026-10-19): what fits our systematic strategies

All claims below come from third-party guides and reviews found via web search, NOT from the firms' own rule pages. Sources often conflict. Verify on the official help centre or agreement before any purchase.

| Firm | Overnight / weekend | Automation (bots) | Drawdown | Fits which Gen114 test |
|---|---|---|---|---|
| Topstep | Flat by 3:10 PM CT (well supported) | TopstepX API allowed; personal device only, no VPS/VPN (one source) | Trailing; intraday vs end-of-day conflicts | T2, T3, T4 (in-session only) |
| Apex | Flat by 4:59 PM ET since "Apex 4.0" (March 2026; one source) | unclear | trailing | T2, T3, T4 |
| Lucid | Not allowed; flat by 4:45 PM ET | Allowed (one of few), no latency arbitrage | End-of-day trailing; LucidPro DLL $1,800 on 100K (one source) | T2, T3, T4 |
| MyFundedFutures (MFFU) | Allowed on Core/Rapid/Flex/Pro, not Builder (one source); another says auto-liquidation 4:10 PM ET | Semi-automated only (human oversight); fully automated bots NOT allowed; HFT capped | Depends on plan (EOD trailing, intraday trailing, EOD static) | T1 if overnight holds are confirmed, with a human confirming orders |
| Tradeify | Overnight allowed (reviews) | unclear | EOD trailing | T1 |

Takeaways:
- Bot-friendly AND flat-by-close: Lucid, Topstep. Only in-session strategies (T2-T4) can work there.
- Overnight-friendly: MFFU (some plans, semi-automated only) and Tradeify. Multi-day trend+carry (T1) only fits these, and MFFU would need you to confirm each order yourself.
- No purchase decisions until a Gen114 test passes and the rules are confirmed on the official pages.

## Update 2026-10-25: overnight + bots check for the futures book


The futures book (Gen205-238, 15 sleeves, Sharpe about 1.2, correlation with crypto about 0.05) holds positions for days, so it
needs a firm that allows **overnight holding AND bots**. Sources are mostly affiliate review sites that disagree with each other;
nothing here is confirmed by a firm. Confirm in the firm's own terms before buying anything.

| Firm / account | Overnight | Bots | Notes from reviews |
|---|---|---|---|
| PropShopTrader Swing (12.5k / 25k) | yes (weekly realised-profit benchmark, weekend holds allowed) | reported allowed ("run your bots"); official FAQ answer not seen | 25k Swing about $595, $2,500 trailing drawdown, 2 E-mini limit, max sim payout $6,000; overnight gap losses are the trader's risk |
| TradeDay | reported yes (overnight + weekend) | unclear | one roundup only |
| Phidias Premium | yes (Premium accounts only) | unclear | |
| Elite Trader Funding Diamond Hands / Direct to Funded | yes (those tiers only) | unclear | |
| FTMO Futures, FundedNext Futures, MyFundedFutures, Lucid, BluSky | mostly no overnight on standard plans | yes (bots explicitly allowed per a Sept 2026 review) | |
| Apex, Topstep, most others | flatten at the close | some allow API bots | not usable for this book |

**Assessment:** a 25k swing account with a $2,500 (10%) trailing drawdown and a 2-contract limit can only run a few of the 15 sleeves with
micro contracts; the earlier estimate (Gen237) was about $6.7k per $50k account over 2 years. Low priority: worth it only as a small,
independent add-on after the crypto accounts run. Next step if wanted: email PropShopTrader to confirm (1) bots on Swing accounts,
(2) micro contracts on bonds / energy / metals, (3) the drawdown type.

Sources: quantvps.com (prop firms swing trading), vettedpropfirms.com (overnight holding; futures swing), prop-memo.com (futures firms that allow bots, 2026-09),
finseeds.com, propscorer.com, fundedtrading.com / propfirmplus.com / traderpayout.com (PropShopTrader reviews), propshoptrader.com policy-update FAQ (2026-01-31).

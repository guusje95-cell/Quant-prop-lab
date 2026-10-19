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

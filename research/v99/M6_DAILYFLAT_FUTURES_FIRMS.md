# M6 (2026-11-03): futures prop firms for the DAILY-FLAT futures book (flat around 16:10 ET and at weekends)

Book: `scripts/futures_paper_dailyflat.py` (DF-1, exact daily-flat: 0.29 / 0.77 / 0.98 in 2010-17 / 2018-22 / 2023-26 backtest; live
planning roughly 0.5). It holds positions from the 18:00 ET Globex reopen until before 16:00 ET, a few daily rebalances, micro / mini
ES, NQ, CL, ZN-type contracts: no HFT, no scalping, no news-only trading, no hedging across accounts.

Everything below is from third-party sources found by web search (official help centres are not reachable from the cloud session).
**Nothing is verified.** `config/prop_sources.json` now lists the official pages; run `get_prop_rules.bat` on the PC to snapshot them,
then record verified rules in the hub dashboard.

| Firm | Bots / API | Close rule | Drawdown ($50K) | Consistency | Payouts | Fit |
|---|---|---|---|---|---|---|
| **Topstep** | official TopstepX (ProjectX) API: REST api.topstepx.com + SignalR; custom bots allowed, HFT banned (Topstep API Access article); API ~$29 / month (one source); some sources: run from a personal device, no VPS / VPN (unconfirmed) | flat by 15:10 CT (16:10 ET) | Combine +$3,000 target, $2,000 end-of-day trailing (locks at start) | Combine: best day <= 50% of profit; XFA: payout eligibility with >= 5 winning days of >= $150 (third-party) | up to 90%; stats 2025: 16.8% of Combines passed, 33.3% of funded traders got a payout, 0.71% called to Live | **candidate 1** (the only firm with an official API) |
| **Lucid Trading** | automated strategies and trade copiers allowed (several sources); HFT / microscalping banned (auto-detected); you bear software errors | flat by 16:45 ET (one source: NinjaTrader strategies force-closed 16:45) | end-of-day trailing, locks at the initial trail balance | LucidFlex none; LucidPro 40-50%; LucidDirect 20% (sources differ); none once live | 90/10; 5 profitable days; min profit per cycle $500 on 50K (LucidPro) | **candidate 2** (via Tradovate / Rithmic API or TradersPost) |
| **Tradeify** | own bots allowed (official Guidelines for Traders), NOT the same bot across other firms; no HFT; may ask for documentation / video proof | close before 16:45 ET (official help page) | EOD trailing | yes (varies by plan) | | **problematic**: "not across multiple firms" conflicts with running one book at several firms |
| **FundedNext Futures** | EAs / bots allowed in challenge and funded (one weak source) | flat by the close | | | | candidate 3 (verify) |
| **Apex** | fully automated bots prohibited on funded (PA) accounts (several sources); semi-automated only | flat by 16:59 ET | | 50% at payout (2026 change; sources conflict) | | **excluded** (no full automation) |
| Alpha Futures | semi-automated requirement, 16:20 close, anti-scalping | | | | | excluded |
| MFFU, Blue Guardian Futures, Funded Futures Family | semi-automated only / bots prohibited | | | | | excluded |

Netherlands: Topstep's eligibility FAQ (help.topstep.com/en/articles/8284116) decides by citizenship + residency, OFAC lists; no
source lists the Netherlands as restricted, but the official table must be checked (some countries get Express Funded but not Live).

How to trade them with our code (all DRY-RUN until the paper gate + user OK):
1. **Topstep**: a `venue_topstepx.py` adapter on the official ProjectX REST API (auth with the user's API key typed in a .bat window,
   never stored), orders limited to the daily-flat book's ES / NQ / CL / ZN micros, forced flat at 15:55 ET, reopen after 18:00 ET.
2. **Lucid / FundedNext**: Tradovate REST API (or Rithmic via NinjaTrader) with the same adapter interface.
3. One book, several accounts: the accounts are highly correlated (same positions), so the edge per account adds up but the risk does
   not diversify. Tradeify's "not across multiple firms" clause has to be checked before using the same book there.

Prop economics v2 (`scripts/v99/df_prop2.py`, `results/v99/df_prop2.json`, Topstep-like rules incl. 50% consistency, 5 winning days,
50% / $5k payout cap, $49 / month, $149 activation; UNVERIFIED rules): mean 2-year net per $50K account
| annual vol | full edge | half edge | zero edge (control) | edge value (full - zero) |
|---|---|---|---|---|
| 10% | $3.2k | $1.4k | $0.3k | $3.0k |
| 18% | $8.6k | $5.2k | $2.9k | $5.7k |
| 24% | $12.7k | $8.5k | $5.2k | $7.5k |
The zero-edge control is still positive at high vol: part of the simulated income is the structure of the program (cheap resets,
convex payouts), not our edge, and real frictions (scaling plans, payout reviews, rule changes, the firm's discretion) are missing.
Plan with the edge value only.

## Index-CFD firms for the same daily-flat equity book (DF-3)
The 8 equity sleeves trade only ES / NQ (R1 also RTY / YM). On index CFDs (US500 / US100 / US2000 / US30) at CFD prop firms the book is
flat over the 17:00 ET rollover, so it pays NO swap and needs no swap-free account. Candidates (EAs allowed, third-party sources):
FTMO (EAs on MT4 / MT5 / cTrader without approval; "each account must run independently, no cross-account copying"), FundedNext,
The5ers, BrightFunded (index CFDs listed; already used for bf), Funded Trading Plus, FundingPips. FTMO-like $100K economics: DF-3.
Index CFD costs (spread, usually no commission) must stay near the futures cost of the backtest (DF-3c: the book is cost-sensitive).

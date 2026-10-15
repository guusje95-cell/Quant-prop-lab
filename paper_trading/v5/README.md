# Paper trading: crypto portfolio v5

**Simulation only.** This uses public Binance market data: no API keys, no account, and it never sends an order.

It runs the exact research code of v5 every hour:
- **Strategies:** C\* + premium carry + liquidation cascade + 4h trend + Weiss expiry.
- **Weighting:** point-in-time equal risk with vol targeting.
- **Ledger:** every completed hour is written to a frozen ledger and never revised.

The plan and the go/no-go rules were fixed in advance in `config/paper_v5.json`.

## Start (Windows)
1. **Pull the latest code:** `git pull`.
2. **Choose one way to run it:**
   - **Simplest:** double-click `paper_v5_start.bat`. It updates every hour at :06. Leave the window open and the PC awake.
   - **No window:** double-click `paper_v5_schedule.bat` once. It creates an hourly Windows task that runs `paper_v5_once.bat`. In Task Scheduler, tick "Wake the computer to run this task", or set sleep to Never.
3. **First run (about 5-10 minutes).** It downloads what is missing since the research pack ends (2026-09-30):
   - 5-minute klines, funding, premium index and open interest for the 20 coins;
   - the full daily spot history of the 10 majors (for C\*);
   - the stablecoin history (for C\*'s filter).

   Later runs take about a minute.

The first run only records the starting point. Paper results start with the next completed hour.

## What you see in the window
Every hour (at :06 UTC; that is :06 Dutch time with the hour +2 in summer and +1 in winter) the window prints the **simulated orders**: what a bot would buy or sell at the start of that hour to reach the new target positions. Example:
```
=== Simulated orders at 2026-10-16 00:00 UTC (paper only, nothing is sent) ===
  BUY  ADA   $     3,159       -2,012 ->     +1,147   (premium carry +3,217, C* -58)
  SELL DOT   $     6,201       +3,923 ->     -2,279   (premium carry -5,865, C* -336)
  positions after: 8 long / 7 short, gross $42,017 on $99,844 equity
```
How to read a line:
- BUY / SELL and the dollar amount;
- the position before -> after (negative = short);
- which strategies caused it.

Most trading happens at 00:00 UTC (daily strategies), every 4 hours (4h trend), after liquidation cascades (limit orders) and on the last Friday of the month at 08:00-10:00 UTC (Weiss). Many hours show "no changes". Changes under $50 are ignored.

All orders are also saved in `paper_trading/v5/orders.csv`. The P&L is booked as if they were filled at the research cost assumptions.

## Daily use
| What | How |
|---|---|
| See how it is doing | `paper_v5_status.bat`, or open `paper_trading/v5/status.md` |
| What a bot would hold next hour | `paper_trading/v5/book_next_hour.json`: dollar notional per coin, cascade limit orders, open cascade trades |
| Share results with Claude (e.g. weekly) | `paper_v5_share.bat`: runs the reconciliation and pushes the ledger / daily / status files (not the market data) |

## Files (paper_trading/v5/)
| File | What it holds |
|---|---|
| `ledger_hourly.csv` | **Frozen.** Per hour: the P&L of each sleeve, its multiplier, the portfolio return, when it was computed, and a *late* flag (more than 2 hours after the hour closed, e.g. the PC was asleep). |
| `daily.csv` | The account per day ($100k, risk 1.0): return, equity, intraday low, daily-stop hits, and HyroTrader 1-Step rule flags (daily / max loss breach, 10% target reached). |
| `status.md` | Summary against the backtest, plus the gate verdict. |
| `orders.csv` | Every simulated order: hour, coin, side, amount, before / after, and which strategy caused it. |
| `events.jsonl` | Every run, error and reconciliation. |
| `reconcile.csv` | The frozen ledger compared with a recomputation on the final data. |

## Go / no-go (config/paper_v5.json)
| Gate | Rule |
|---|---|
| Minimum | 56 days and at least 2 Weiss expiry events |
| Reconciliation | Frozen vs recomputed: correlation >= 0.99 and difference <= 0.5% of the account |
| Operations | At most 5% late hours; no data errors |
| Performance | z against the backtest. **GO** if z > -1; **EXTEND** to 112 days if -2 <= z <= -1; **STOP** if z < -2 or drawdown is worse than -12% |

Be honest about what 8 weeks can show: it mainly proves that the pipeline works live (no look-ahead, no gaps). It cannot prove the edge.

## Notes
- **If Binance refuses your location**, the tool stops and logs `DATA_REFUSED`. Do not use a VPN to get around it; tell Claude, and the feed can be switched to a source you are allowed to use.
- **The sleeves' costs and funding** are the research values. Real prop-firm fills come later, in a demo/testnet phase.
- **Self-test (no-look-ahead proof on the research data):** `python scripts/paper_v5.py selftest`.

# Gen49–51: two more papers, then a search for something better than C* (pre-registered)

- **Protocols:** `config/gen49_protocol.json`, `gen50_protocol.json`, `gen51_protocol.json`, each written before its runs.
- **Scripts:** `scripts/gen49_research.py`, `gen50_research.py`, `gen51_prop_risk_tools.py`, `gen51_hourly_check.py`.
- **Results:** `results/gen49_research.csv`, `gen50_research.csv`, `gen51_prop_risk_tools.csv`.
- **Trials:** about 30 runs in these generations. The project total is now about 290.

## Gen49: the two new papers + combinations

| Test | Result | Verdict |
|---|---|---|
| **Bianchi et al. 2023** commodity curve slope dynamics (2-contract version, 8 bp) | Net Sharpe −12. Before costs: continuation −2.9, *reversal* +2.9. That mirror image is a stale-price artifact: the far contracts trade rarely, so pysystemtrade's daily "last price" for them is often old. The paper uses synchronised settlement prices. | **Data unsuitable / rejected.** The reversal artifact is not traded. |
| **Liu & Tse 2017**, hold overnight (US500 CFD, 1 bp + 1 bp/day financing) | −0.14. Before costs it earns +5.5% a year (Sharpe 0.51), but costs remove it; 0.35 even at futures cost. | Rejected |
| Liu & Tse: fade the overnight move in the first half hour / follow it in the last half hour | −1.7 … −1.0 | Rejected |
| **Baltussen et al. 2021**, rest-of-day → last 30 min | US500 −0.29, US100 −0.19 | Rejected |
| Noise-area breakout on US500 + US100 + US30 together | 0.22 | Not passed |
| C* + portfolio-level Moreira-Muir overlay | 1.54 vs 1.69, with a deeper drawdown | Rejected |
| Equal-risk multi-strategy (C*, noise-area, vol-managed S&P, curve momentum) 2018-09…2023-09 | 1.31 vs C* 1.78 (same window). Sleeve correlations are about 0, but the weak sleeves dilute C*. | Rejected |

## Gen50: independent crypto trend replication + smarter combinations

| Test | Sharpe | Verdict |
|---|---|---|
| **Zarattini, Pagani & Barbon 2025 "Catching Crypto Trends"** ensemble (5–360-day channels, midpoint exit), same 10 coins | **1.44** (CAGR 17%, MDD −14%) | An **independent confirmation** that the crypto trend edge is real |
| C* + CCT 50/50 | 1.60 vs C* 1.69. FTMO pass rate goes up 54% → 61%, but profit goes down. | Not passed |
| C* × S&P 500 200-day regime filter | 1.95 vs 2.00 (to 2024-03) | Rejected |
| Sharpe-weighted multi-strategy | 1.61 vs 1.78 | Rejected |

## Gen51: prop-specific risk tools on C*

**CFT 1-Phase $100k, budget 5, 24 months, daily-candle simulation:**

| Variant | Pass / attempt | Daily-loss fails | Funded | Net avg | Net typical | P(profit) |
|---|---|---|---|---|---|---|
| Plain C* | 35% | 25% | 96% | $9,343 | $4,754 | 75% |
| **Daily equity stop at −3%** | **41%** | **0%** | 97% | **$11,859** | **$9,468** | **92%** |
| Cushion scaling | 56% | 17% | 94% | $6,837 | $3,331 | 77% |
| Both | 60% | 0% | 91% | $7,341 | $5,175 | 80% |

**Other firms with the daily stop:**
- FTMO 2-Step: pass 54% → 73%.
- CFT 2-Phase: pass 65% → 76%.

**Hourly reality check, 2022–2026:** daily C* weights replayed on hourly prices. The stop triggers on the real hourly equity path and fills at that hour's close minus 0.1%.

| CFT 1-Phase | Pass / attempt | Net avg | P(profit) |
|---|---|---|---|
| Hourly, no stop | 37% | $6,352 | 81% |
| Hourly, real stop | **44%** | $5,790 | 79% |

**What the hourly check shows:**
- **The daily-candle model is too pessimistic about C\*.** It assumes all coins hit their lows together, giving a worst day of −12.3%. On the real hourly path the worst day was −8.1%, and C* passes more often (37% vs 28% in the same period).
- **Real stop fills are worse than assumed.** On the 7 stop days the average was −4.1% and the worst −8.2%, against the assumed −3.3%.
- **So the stop reliably adds about 6–7 points of pass rate and removes daily-loss fails.** Its effect on 2-year profit is uncertain: between −9% and +27%. Per the pre-registered rule this is **NOT PASSED** (profit not proven higher).
- It is available in the app as an optional "own risk tool", with this caveat attached.

## Bottom line

- **C\* is still the best strategy** found in about 290 pre-registered trials.
- **Its edge is confirmed by an independently designed system** (CCT, Sharpe 1.44 on the same coins).
- **Nothing tested in Gen47–51 beats C\*** on Sharpe or on 2-year prop profit.
- **The most useful practical findings for prop trading:**
  1. C*'s real prop odds are better than the daily-candle model shows.
  2. A daily equity stop below the firm's daily limit raises the pass rate by about 6–7 points, but don't count on it raising profit.

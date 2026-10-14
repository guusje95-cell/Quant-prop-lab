# Gen53: literature-based improvements to crypto trend (pre-registered)

- **Protocol:** `config/gen53_protocol.json`.
- **Scripts:** `scripts/gen53_download.py`, `gen53_research.py`, `gen53b_followup.py`, `gen53c_btc_leads_pit.py`.
- **Results:** `results/gen53_research.csv`, `gen53_h5_prop.csv`, `gen53_btc_leads_pit.csv`.
- **Dashboard:** https://claude.ai/artifact/4M2JZaEc7DjxZEDcUaN9HU
- **Setup:** all strategies scaled to 15% volatility using DEV (2018-03 → 2022-12) only. TEST = 2023-01 → 2026-10.

## H1: survivorship bias (Grobys, Sandretto & Äijö 2026; Stöckl et al. 2022)

**Data:** Yahoo daily candles for 54 coins that were in the top 20 at some point in 2017–2026, including collapsed ones (LUNA classic, FTT, EOS, XEM, BSV, BTG, WAVES, OMG …). MATIC and pre-2023 IOTA are missing on Yahoo.

| Universe (same Yahoo data) | Sharpe | DEV | TEST | CAGR | Max DD |
|---|---|---|---|---|---|
| Fixed 10 majors (today's winners) | 1.78 | 2.06 | 1.50 | 32.6% | −19.0% |
| Point-in-time top 10 by 30-day volume | 1.27 | 1.23 | 1.32 | 18.5% | −13.9% |
| Point-in-time top 20 | 1.44 | 1.44 | 1.43 | 21.6% | −14.3% |

**What this means:**
- Choosing today's 10 majors inflated the 2018–2022 results by about 0.6–0.8 Sharpe.
- Over 2023–2026 the gap is small.
- The honest forward expectation for C* is a Sharpe of about 1.3–1.5.
- Under the protocol, a point-in-time top 10/20 universe is an acceptable forward universe (its TEST Sharpe is within 0.2 of the fixed list).

## H5: "BTC leads" — hold altcoins only while BTC's own C* signal is positive: **PASSED**

| Universe | C* Sharpe (TEST) / MDD | + BTC leads Sharpe (TEST) / MDD |
|---|---|---|
| Fixed 10 majors (Binance) | 1.69 (1.50) / −15.1% | **1.78 (1.63) / −13.1%** |
| Point-in-time top 10 (Yahoo) | 1.27 (1.32) / −13.9% | **1.37 (1.50) / −12.8%** |
| Point-in-time top 20 (Yahoo) | 1.44 (1.43) / −14.3% | **1.52 (1.52) / −13.4%** |

**Prop results with challenge risk 1.0, funded 0.4 (24 months, up to 5 buys):**

| | TEST net (daily) | HOURLY pass | HOURLY net | HOURLY P(profit) |
|---|---|---|---|---|
| CFT 1-Phase, C* | $2,208 | 31% | $10,157 | 97.7% |
| **CFT 1-Phase, C* + BTC leads** | **$3,018** | **33%** | **$11,563** | 97.7% |
| FTMO 2-Step, C* | $6,874 | 63% | $10,921 | 97.2% |
| **FTMO 2-Step, C* + BTC leads** | **$7,837** | **64%** | **$12,062** | **97.7%** |

**Verdict:** this is the first robust upgrade to C* since gen38. It helps on all three universes and in both periods, it lowers drawdowns, and it improves prop results on hourly prices.

**Available in the app:** C* parameter `btc_leads`, and the Scorecard entry "C* + BTC leads (Gen53)".

## Other tests

| Test | Sharpe | TEST | Max DD | Verdict |
|---|---|---|---|---|
| H2 rebalance tranching: 4 schedules 00/06/12/18 UTC (Hoffstein, Faber & Braun 2020), OKX hourly | 1.74 (vs 1.73) | 1.55 (vs 1.48) | −14.8% (vs −15.2%) | Not passed (+0.07 < +0.10). Smoother: worst day −4.5% vs −4.9%; CFT net on the OKX hourly path $4.9k vs $3.1k |
| H3 AHL continuous trend signal (Baz et al. 2015), alone | 1.12 | 0.77 | −17.0% | Rejected |
| H3 C* + AHL 50/50 | 1.52 | 1.25 | −13.6% | Rejected |
| H4 portfolio-volatility targeting with EWMA covariance (cap 2×) | 1.36 | 1.06 | −17.1% | Rejected. It levers up weak-signal periods. |

## Recommendation

1. **Use "C\* + BTC leads"** in place of plain C*, with prop settings 1.0× in the challenge and 0.4× when funded. For FTMO, also see the Gen52 optimised settings.
2. **Plan with Sharpe ≈ 1.4–1.5**, not 1.7, because of the survivorship check.
3. **Optional:** split the daily rebalance into 4 slots (00/06/12/18 UTC) for a slightly smoother ride. This needs execution 4 times a day.

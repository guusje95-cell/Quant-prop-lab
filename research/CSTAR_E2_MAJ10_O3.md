# C*: E2 on 10 crypto majors + stablecoin-liquidity overlay (gen36–38)

Status: **meets the user target (net Sharpe > 1.3 and CAGR > 15%, 2018–2026) under the pre-registered gen38 checks U1–U5.**
- Protocols: `config/crypto_gen36..38_protocol.json`.
- Results: `results/crypto_gen38_final.json`.

## Rules
- **Coins:** BTC, ETH, BNB, XRP, ADA, SOL, DOGE, AVAX, DOT, LINK (USDT perps on Bybit). Long-only. Rebalance once a day right after 00:00 UTC.
- **Signal per coin:** frozen E2 (the 15-rule breakout + 4-rule momentum average).
- **Stablecoin overlay (O3):** look at the 30-day change of USDT+USDC market cap.
  - Growing: signal × 1.25.
  - Shrinking: signal × 0.75.
  - Data comes from the free Coin Metrics community API, with a 1-day lag.
- **Size:** w = signal × O3 × min(1, 0.40 / 30-day vol) / N × 0.7916. That's 15% target vol; average gross exposure 13% of equity, maximum 80%.
- **Daily command:** `python scripts/cft_e2_signal.py --equity <E> --mode personal`

## Evidence (net of 7.5 bp/turnover, 0 swap)

| Period | Net Sharpe | CAGR | Max DD | Worst intraday day |
|---|---|---|---|---|
| 2018–2026 | **1.67** | **24.1%** | −14.1% | −12.3% |
| 2018–21 (DEV) | 2.14 | 36.3% | −9.6% | −7.6% |
| 2022–23 (VAL) | 1.26 | 13.2% | −8.1% | −4.9% |
| 2024–26-10 (TEST) | 1.19 | 16.0% | −14.1% | −12.3% |
| Fresh 2026-05 → 10 | 2.01 | – | −2.7% | −2.6% |

- **Returns by year:** 2018 −4.4%, 2019 +28.7%, 2020 +58.8%, 2021 +76.6%, 2022 −5.3%, 2023 +35.2%, 2024 +42.2%, 2025 +0.5%, 2026 YTD +5.6%.
- **2× costs + funding:** Sharpe 1.47 / CAGR 20.8% (all); 0.95 (TEST).
- **1-day delay:** 1.59 (all); 0.72 (TEST).
- **Robustness:** bootstrap Sharpe 95% CI [0.87, 2.39]. Deflated Sharpe (N = 136 trials) = 0.99. Newey-West t = 4.07.
- **Leave-one-coin-out:** Sharpe 1.59–1.73.
- **Independent replications (gen37):**
  - E2 on untouched coins ranked 11–30: Sharpe 0.96, positive in every period.
  - O3 improves every period on the 8 alts and on coins 11–30 (pooled p = 0.03).

## Where it does NOT fit
**CFT accounts at this risk level.** The worst intraday day (−12%) breaches the 4–5% daily loss.
- For CFT, use the gen34 two-speed pipeline (playbook). Adding O3 there did not improve it: 24-month net +5.6% vs +7.6% on 2023–24 starts.
- C* at 15% vol is a strategy for an own Bybit account, or for a prop firm without an equity-based daily loss.

## Caveats
- **Recent weakness:** 2024–26 Sharpe is 1.19, below 1.3; 2025 was flat.
- **Partly seen data:** the E2 design was formed after gen26 had seen 2023–26 data.
- **Delay sensitivity:** a 1-day execution delay hurts recent results.
- **Data proxy:** the backtest uses Binance spot candles as a proxy for Bybit perps.
- **Still a risk of loss.** Paper trade first.

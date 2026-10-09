# CFT playbook: E2 LIQUID2 (BTC + ETH daily trend/breakout, long-only)

Status: **APPLICABLE under the gen31 pre-registered gates for CFT 1-Phase (Bybit route)**. The 2-Phase version narrowly failed one gate.
Nothing here is a guarantee. Protocols: `config/crypto_gen28..31_protocol.json`. Results: `results/crypto_gen31_ev.json` and `results/crypto_gen31_robustness.json`.

## Rules (frozen, no discretion)
1. **Instruments:** BTCUSDT and ETHUSDT perpetuals on CFT's Bybit route. Bybit fees apply and there is no swap.
2. **When to trade:** once per day, right after **00:00 UTC**, and before the 00:05 UTC daily-loss reset if possible. Use completed daily candles only.
3. **Signal per coin:** `scripts/cft_e2_signal.py` computes it.
   - Score s = 0.5 × (average of 15 "close above n-day high → long for h days" rules, n ∈ {5,7,10,14,20}, h ∈ {1,2,3}) + 0.5 × (average of 4 "n-day return > 0" rules, n ∈ {14,30,60,90}).
   - Short components are clipped at 0, so the strategy is long-only.
4. **Size:** target notional = equity × L × s × min(1, 0.40 / 30-day annualised volatility) / 2.
   - 1-Phase: L = 0.3203 (risk level v = 6% annual volatility).
   - 2-Phase: L = 0.4270 (risk level v = 8%).
   - Typical total exposure is 5–10% of equity, with a maximum of 32% (1-Phase).
5. **Rebalance:** adjust to the target every day. Use limit orders where possible; the backtest assumes taker fees + 2 bp slippage.
6. **No stop orders and no discretionary overrides.** Do not add other coins: alts caused all the breaches in gen28–30.
7. **Run:** `python scripts/cft_e2_signal.py --equity <equity> --program 1PHASE`. It reads public Bybit data, needs no API key and never places orders.

## Evidence

**Strategy at the 1-Phase risk level (net of 7.5 bp/turnover):**

| Period | Net Sharpe | CAGR | Max DD | Worst intraday day |
|---|---|---|---|---|
| 2018–2026 | 1.36 | 8.2% | −6.7% | −3.7% |
| 2023-01 → 2026-10 | 1.24 | 7.3% | −5.9% | −3.6% |
| Never-seen 2026-05-24 → 10-08 | 1.68 | – | −1.3% | – |

- Calendar-year returns: 2018 −2.9%, 2019 +16.0%, 2020 +24.6%, 2021 +13.9%, 2022 −4.4%, 2023 +11.3%, 2024 +12.3%, 2025 +2.2%, 2026 YTD +2.2%.
- Profitable at 2× costs plus funding (TEST net Sharpe 0.95).
- With a 1-day execution delay, net Sharpe is 1.05 (TEST) and 1.20 (all).
- Newey-West t = 3.4. Deflated Sharpe (N = 112 crypto trials) = 0.93.

**CFT simulation (equity-based daily loss on real Binance daily lows, all lows assumed simultaneous; no stops):**

| 1-Phase, v = 6% | Pass | Daily fail | Max (trailing 6%) fail | Not passed within 548 d | Median days to pass | Expected value per attempt* |
|---|---|---|---|---|---|---|
| Starts 2023-01 → 2024-06 (gate) | 78% | 0% | 0% | 22% | 222 | +3.7% of account |
| Starts 2018 → 2024-06 | 70% | 2% | 8% | 20% | 242 | +5.8% |
| Block bootstrap (2,000 paths) | 62% | 1% | 18% | 19% | 246 | +3.9% |
| 2× costs + funding | 61% | 0% | 16% | 23% | – | +1.4% |
| Trades 1 day late | 64% | 14% | 0% | 23% | – | ~+1.5% |

\* Expected value per attempt = 0.95 × expected payouts in the first 12 funded months (80% split) − fee (0.8% of account). Example: on a $100k account, +3.7% ≈ +$3.7k expected per attempt. This is an average across starts, not a promise.

**2-Phase (v = 8%):**
- 2023–24 starts: pass 77%, daily fail 0.4%.
- Expected value per attempt is +0.3% at a 0.9% fee and −0.3% at a 1.5% fee, which failed G3. Truncated funded windows make this conservative.
- Bootstrap: pass 61%, expected value +4.7% per attempt.

## Honest caveats
- **It is slow.** At this risk level the strategy makes about 7–8% a year, and 2025–26 were weak (+2%/yr). Expect about 8 months to reach +10%, and about 1 in 5 attempts will still be open after 18 months.
- **Overfitting risk.** The E2 design was formed after gen26, which had seen 2023–26 data for these coins. Only 2026-05-24 → 10-08 is truly unseen data, and it is short. 115 crypto trials were run in total.
- **Rules are uncertain.** The CFT rules, fees, time limit and the funded-stage rules are UNCERTAIN; check them at checkout. The simulation applies the challenge rules to the funded stage as well.
- **Execution timing matters.** A 1-day execution delay turns crash days into daily-loss breaches (14%). Trade on time.
- **Data.** Binance spot candles are a proxy for Bybit perps. Bybit wicks can be deeper.
- **Paper trade first.** Before paying for a challenge, paper trade with `scripts/cft_e2_signal.py` for a few weeks.

---
# UPGRADE (gen34): TWO-SPEED 1-Phase pipeline — RECOMMENDED

Status: **passes the pre-registered gen34 'BETTER' gate.**
- Protocol: `config/crypto_gen34_protocol.json`.
- Results: `results/crypto_gen34_twospeed.json` and `results/crypto_gen34_robustness.json`.
- The signal is unchanged: the same frozen E2. What changes is the risk used in each stage.

| Stage | Coins | Risk (multiplier L) | Command |
|---|---|---|---|
| Challenge (1-Phase) | 10 majors: BTC ETH BNB XRP ADA SOL DOGE AVAX DOT LINK | v = 15% (L = 1.0251) | `python scripts/cft_e2_signal.py --equity <E> --mode challenge` |
| Funded | BTC + ETH | v = 6% (L = 0.3203) | `python scripts/cft_e2_signal.py --equity <E> --mode funded` |

**Why it works:**
- A failed challenge only costs the fee (about 0.8% of account size). So you trade the challenge fast, accept more failures and simply re-buy.
- Once funded, the account is the asset, so you trade it slowly and safely.
- If the funded account is ever breached, start a new challenge.

**24-month pipeline results** (net = payouts − all fees, as a fraction of account size):

| | Two-speed (new) | Single-speed (gen31) |
|---|---|---|
| Median months to funded, 2023–24 starts | **4.0** | 8.2 |
| Funded within 90 days / 180 days | **40% / 68%** | 11% / 28% |
| Mean net over 24 months, 2023–24 starts | **+7.6%** (P>0 98%) | +3.6% (P>0 65%) |
| Mean net, all starts 2018–24 | **+11.0%** (P>0 92%) | +7.5% |
| Mean net, bootstrap (1,000–2,000 paths) | **+7.7%** (P>0 83%) | +5.4% (P>0 68%) |
| Challenges bought on average | 2.1–3.6 | 1.1–1.4 |

**Robustness** (mean net over 24 months, two-speed):

| Condition | 2023–24 starts | All starts 2018–24 | Bootstrap |
|---|---|---|---|
| Fee 1.5% | +6.1% | +9.0% | +5.3% (P>0 71%) |
| 2× costs + funding | +5.8% | +9.3% | +5.9% |
| 1-day execution delay | +1.9% (median −0.9%) | +8.3% | +6.1% |

**2-Phase two-speed** (challenge BTC+ETH at v = 20%, funded at v = 8%):
- Strong on bootstrap (+9.4%, P>0 81%) and on all starts (+11.3%).
- Weak on 2023–24 starts (+1.7%, P>0 35%).
- **1-Phase is preferred.**

**Extra caveats:**
- The challenge leg holds alts, which can wick −50% to −85% in a crash (2025-10-10). Expect challenge breaches; they are priced in.
- Re-buying requires discipline. Budget for about 3–4 fees.
- CFT funded rules, fees and the time limit are UNCERTAIN.
- The 2-Phase funded risk (v = 8%) sits at the top of the grid that was searched.

# Gen86: more CFD sleeves (2026-10-18)

- **Protocol:** `config/gen86_protocol.json`, registered before any number was computed. 6 trials.
- **Scripts:** `scripts/gen86_cfd.py` (tests) and `scripts/gen86_bookcheck.py` (book check).

| Test | Events | DEV 20-22 | TEST 23-24 | HOLD 25-26 | Hit rate | bp per event | Book 2022-26 (1.618)* | Verdict |
|---|---|---|---|---|---|---|---|---|
| E1 CME expiry fade (last Friday, 16:00 London, exit 18:00) | 81 | 0.36 | -0.08 | 1.77 | 61% | +15 | 1.69 | rejected: TEST < 0.5. **Watchlist** |
| E1 variant exit 17:00 | 81 | 0.54 | -0.43 | 1.24 | 52% | +10 | 0.99 | variant |
| E2 crypto weekend -> Monday US100/US500 | 315 | -0.05 | 1.57 | -0.78 | 51% | +0.5 | 1.77 | rejected: DEV < 0, HOLD < 0.3 |
| E2 variant only when weekend move > 2% | 87 | 0.54 | 0.97 | -1.07 | 51% | +10 | 1.71 | variant |
| E3 pre-FOMC drift on BTC/ETH CFDs | 53 | 1.02 | 0.20 | -0.21 | 60% | +69 | 0.81 | rejected |
| E3 variant exit 16:00 New York | 53 | 1.46 | -0.51 | -0.66 | 55% | +80 | 0.79 | variant |

\* **Book check:**
- The P1 construction gives a sleeve weight only after 30 active days in the past year.
- The first run therefore left the rare-event sleeves (E1, E3) out of the book.
- `gen86_bookcheck.py` reruns the check with the 6-event rule that Weiss uses.
- The verdicts do not change: all of them already fail the per-period rule.

**Why E1 and E2 are rejected even though they raise the full-period book Sharpe:**
- The gain comes from one period only: HOLD for E1, TEST for E2.
- That one-period pattern is what the split rule is there to catch.
- **E1 (CME expiry fade) goes on the watchlist.** It has 81 events, the paper ledger can track it from now on, and it is to be re-tested in 2027 with fresh data.

## Running tally for the CFD route

- About 55 ideas tested (Gen39-42, Gen73-78, Gen81-86).
- **In the book:**
  - C\* (now swap-aware);
  - Weiss expiry;
  - plus premium carry and trend 4h, on swap-free accounts only.

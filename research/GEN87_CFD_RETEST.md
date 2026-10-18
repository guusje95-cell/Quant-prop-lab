# Gen87: re-testing crypto sleeves inside the CFD book (2026-10-18)

- **Protocol:** `config/gen87_protocol.json`, registered before any number was computed. 4 trials.
- **Script:** `scripts/gen87_cfd.py`.
- **Books compared:** the Gen85 CFD book (1.618) and the swap-free book (1.813).

| Test | DEV 20-22 | TEST 23-24 | HOLD 25-26 | Corr C* | CFD book after | Swap-free book after | Verdict |
|---|---|---|---|---|---|---|---|
| R1 dip-buy in uptrends, 11 CFD coins | 0.21 | 0.93 | 0.58 | 0.10 | 1.584 | 1.829 | rejected: passes alone, lowers the CFD book |
| R2 cascade strict, BTC/ETH CFDs | -0.13 | -0.03 | -0.82 | 0.03 | 1.697 | 1.849 | rejected: loses money alone* |
| R3 trend 4h, BTC/ETH only | 0.78 | 1.26 | 0.05 | 0.35 | 1.431 | 1.794 (replacing trend 4h) | rejected |
| R4 dip-buy BTC/ETH (variant) | 0.53 | -0.09 | 0.26 | 0.03 | 1.618 | 1.813 | variant |

\* **R2:** a sleeve that loses money on its own can still lift the full-period book Sharpe as a hedge. A gain that comes only from the hedge, with negative standalone P&L, is not something to trade.

**R1 in the swap-free book (+0.016):**
- This was reported for information only and was not a pre-registered adoption test.
- It is too small to act on.

**Conclusion:**
- Every crypto sleeve on file has now been tested against both CFD books.
- With the data available, the books stay as they are: CFD 1.62, swap-free 1.81.

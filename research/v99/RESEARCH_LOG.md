# v9.9 research log (crypto, after the v9.8 freeze)

Started 2026-10-27. Target: a candidate with an estimated live Sharpe >= 2.0 after realistic execution costs and a credible
selection-bias adjustment, validated out of sample. v9.8 stays frozen and paper-trades unchanged.

## Baseline protection
- The live paper baseline is v9.8 (`QPL_PAPER=v98`, `paper_v98_*.bat`, `config/paper_v98.json`), run on the user's PC from this branch.
  Files it executes or reads: see `config/v98_freeze.json` (sha256 per file + git tree hashes of the research-data folders).
- Guard: `python scripts/v99/check_v98_freeze.py` must print `v98 FREEZE OK` before every commit of v9.9 work.
- All v9.9 code lives in `scripts/v99/` and `research/v99/` and only IMPORTS the frozen modules (never edits them). Results go to
  `results/v99/`. Nothing here is promoted to paper without the user's explicit approval.
- Validation periods (unchanged project discipline): development 2022, validation 2023-24, holdout 2025-26 (the holdout has been
  seen many times in this project, so it is not a clean holdout; see the methodology audit). The paper period from the v98 start is
  the only genuinely unseen data.

## Experiments
| ID | Date | Direction | What | Result | Decision |
|---|---|---|---|---|---|
| A1 | 2026-10-27 | audit | estimated-live-Sharpe methodology: project method reproduced (1.668 at N = 1,849), DSR, Harvey-Liu, CSCV/PBO on 502 sleeve-subset books, Lo autocorrelation, block bootstrap (`METHODOLOGY_AUDIT.md`) | project 1.67; HL-BHY 2.56; PBO 0.13; best-of-502 decay 0.64; execution-honest 3.28 | gate kept: execution-honest SR - E[max] (N = 1,849 + v9.9 trials) >= 2.0 |
| R1 | 2026-10-27 | execution | limit orders at the touch for the daily sleeves' part of the 00:00 net trades, 20 pack coins with 5-min OHLC; full fill only on a trade-through by delta, else cross at window end (`r1_limit.py`, `r1_protocol.json`, 8 variants) | control (v9.8, Bybit taker on net trades) 3.283 [3.082, 3.959, 2.720]; central o=0/W60/d1: **3.377** [3.162, 4.057, 2.817], fill 96%, +4.2 bp per order; best o=2/W60/d1 3.382; conservative o=2/delta3/delay10: **3.287 [3.041, 3.946, 2.763]** (2022 lower) | **investigate further, not promoted**: the gain is +0.10 central but about 0 under conservative fills; OHLC cannot model queue position. Next: measure real fill rates in the dry-run bot (no effect on v98), or trade-level data |
| R3 | 2026-10-27 | allocation | quarterly walk-forward MV tilt (Sharpe and correlation shrunk 50%, multipliers 0.5-2, max 0.5 change per quarter), lambda 0.25 / 0.5 / 1 (`r3_allocation.py`, `r3_protocol.json`) | v9.8 3.240 [3.063, 3.910, 2.670]; chosen lambda 0.25: 3.235 [3.070, 3.896, 2.664]; 0.5: 3.228; 1.0: 3.205. Past-data tilt mostly cuts ridge ML (0.7-0.9x) and adds basket / C* | **rejected**: equal risk stays. The full-sample hints (Weiss up, ridge down) are not recoverable from past data; Weiss's sparse daily P&L makes its estimated Sharpe low |
| H1 | 2026-10-30 | event / regime (hub agent, FLAGGED post hoc) | first autonomous hub experiment `agent:event_short_vol_regime`: event short x0.5 when BTC 30-day vol (known the day before) is above its trailing-1-year median (45% of days) | v9.8 3.240 [3.063, 3.910, 2.670] -> **3.336 [3.122, 3.971, 2.817]**: +0.096, every period up; pre-registered rule: pass | **investigate further** (post hoc: the regime effect was seen in Gen473 first): robustness of the multiplier / window, execution-honest version, then a candidate only with the user's OK |

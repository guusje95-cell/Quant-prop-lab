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

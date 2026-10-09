# V6 Next Actions (resume point)

Branch: `claude/autonomous-prop-quant-research-191f8d`.

To resume, run these first:
```bash
cd Quant-prop-lab
pip install -r requirements.txt lightgbm hmmlearn arch ruptures
# data is git-ignored; restore pinned sources:
git clone --depth 1 --filter=blob:none --sparse https://github.com/robcarver17/pysystemtrade.git data/raw/ext/pysystemtrade && \
  (cd data/raw/ext/pysystemtrade && git sparse-checkout set data/futures/adjusted_prices_csv data/futures/multiple_prices_csv data/futures/csvconfig data/futures/fx_prices_csv && git checkout bbe29e19)
git clone --depth 1 https://github.com/coinmetrics/data.git data/raw/ext/coinmetrics-data      # pinned f1a36afb
python -m pytest -q tests                     # expect 88 passed
python scripts/v6_registry.py                 # regenerate v6/V6_HYPOTHESIS_REGISTRY.csv
python -c "import sys;sys.path.insert(0,'src');from qpl.research import factory as F;print(F.verify_ledger())"
bash scripts/run_v6.sh                        # reproduces all V6 experiments (re-runs tagged QPL_LEDGER_TAG=repro)
```

## State at checkpoint (2026-10-09)
Done:
* **CT1 decay diagnosis.** CT1 is conditional long BTC beta; the short leg never paid; shorter-horizon persistence vanished 2024–26.
* **Futures panel.** Built, audited and cross-validated.
* **gen13.** Trend + carry ELIGIBLE; XS momentum/value/skew REJECTED.
* **gen14.** Buffering adopted; implementable at about $1M+.
* **gen15.** Regime, change-point, factor-momentum and ML layers REJECTED.
* **Statistics.** PBO 0.017; DSR; MinTRL.
* **Crypto.** Coin Metrics cross-section and on-chain factors REJECTED.
* **Portfolio.** CT1 vs futures analysed.
* **F9 frozen.** Futures paper book and CLI built and tested.

Open questions / incomplete:
1. **No prospective data.** The futures paper book needs user-supplied pysystemtrade-format data after 2024-03. Nothing can be fetched here.
2. G15-SMALL (a small-account micro-contract universe) is not yet designed.
3. Weekly continuation in alts (gen16 by-product) is logged only.
4. CT1-LF (long/flat) is registered for the prospective trial only.

## Highest-value next experiments (ranked by information gain ÷ cost)
1. **Prospective F9 paper book (needs user data).** Each trading day after updating the data directory:
   ```bash
   python scripts/paper_futures_step.py --data-dir <dir> --capital 1000000
   ```
   Review at 6 and 12 months against `config/f9_spec.json`: kill at 25% drawdown, drift z < −2 after 252 days. Compare realised fills and costs with the model's 1× cost estimate. That cost comparison is the most decision-relevant unknown.
2. **Prospective CT1 + CT1-LF crypto paper** (spot and perp separately) at 0.30× book:
   ```bash
   python scripts/paper_crypto_step.py --bars <daily csv> --account spot --start <date>
   ```
3. **G15-SMALL design.** Choose about 12–20 micro/mini contracts by *non-performance* criteria: one per major underlying cluster, cost/vol ≤ 0.01, notional ≤ 5% of capital. Then evaluate on DISCOVERY+VALIDATION only, under a new pre-registered protocol, for $100k–$250k accounts. This is the only route for a smaller personal account.
4. **Data acquisition** (`v6/V6_DATA_CATALOG.md` backlog). Binance public data with delisted symbols would unlock spot–perp basis, executable perp prices and a survivorship-free alt universe.
5. **Cost realism.** If any real fill data becomes available, calibrate slippage per instrument and re-run gen13/14 at measured costs. The edge is cost-sensitive (3× ≈ break-even in VALIDATION without buffering).
6. **Lower-priority research** that is still clean on available data:
   * futures carry *term-structure shape* (carry slope across contracts beyond the next one; needs per-contract data, not in the repo);
   * trend signal decay study across 50 years (structural-break test on the trend premium);
   * crypto weekly continuation with turnover control on Coin Metrics VALIDATION (2021–22), under a new protocol.

## Do not repeat
* Regime/timing filters on trend or carry: rejected 3× across asset classes.
* Short-horizon BTC calendar, funding contrarian, funding carry without basis data, on-chain MVRV value/timing, crypto XS momentum at weekly frequency with 30 bp costs: all rejected.
* Re-tuning on futures 2014–2024 or BTC 2024–2026: these periods are used.

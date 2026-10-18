# To do at home (for Claude's research)

Double-click each file in the `Quant-prop-lab` folder, wait until it says Done, then push (commands below).

1. **`get_coinbase.bat`**: Coinbase BTC/ETH hourly, about 10-20 min.
   - Used for Gen88, the Coinbase-premium test (`config/gen88_protocol.json`). Its rules are already registered.
2. **`get_binance_extra.bat`**: about 40 more Binance coins, several hours; it keeps the PC awake itself.
   - Used for Gen80, the breadth test: premium carry, cascade and dip-buy on more coins.
3. **`paper_v5_share.bat`**: shares the paper-trading results for the weekly reconciliation check.
4. **Optional:** a Databento futures trial (`get_databento_check_cost.bat` shows the cost first; do not pay without deciding).
   - Used for the index near-misses at futures costs.

**After 1-3:**
```
git pull --no-edit
git add research_data paper_trading
git commit -m "data from home"
git push
```
Then tell Claude: "data is pushed".

**Before buying a CFD challenge:**
- Ask the firm in writing whether crypto CFDs can be swap-free (FundedNext: add-on, +10% fee).
- Ask what the crypto swap rate is.
